/**
 * KE04 Loading Firmware
 * Main
 *
 * Kevin Cuzner
 */

#include "MKE04Z4.h"

#define BUFFER_LENGTH 64
#define API_STATUS_CMD_SHIFT 0
#define API_STATUS_CMD_MASK (0x7 << API_STATUS_CMD_SHIFT)
#define API_STATUS_READY_SHIFT 3
#define API_STATUS_READY_MASK (0x1 << API_STATUS_READY_SHIFT)
#define API_STATUS_STATUS_SHIFT 4
#define API_STATUS_STATUS_MASK (0xF << API_STATUS_STATUS_SHIFT)
#define API_STATUS_STATUS(V) ((V & 0xF) << API_STATUS_STATUS_SHIFT)
#define API_STATUS_ERROR_SHIFT 8
#define API_STATUS_ERROR_MASK (0xFF << API_STATUS_ERROR_SHIFT)
#define API_STATUS_ERROR(V) ((V & 0xFF) << API_STATUS_ERROR_SHIFT)
#define API_STATUS_CMD_ERASE 0
#define API_STATUS_CMD_PROGRAM 1
#define API_STATUS_OK 0
#define API_STATUS_ERR_FLASH 1
#define API_STATUS_ERR_NOT_IMPLEMENTED 15

#define FCMD_MERASE 0x8


typedef struct
{
    volatile uint32_t status;
    volatile uint32_t address;
    volatile uint32_t length;
    volatile uint32_t buffer[BUFFER_LENGTH];
} APIState;

__attribute__((section (".flash_api_state"), used))
APIState FlashAPIState;

/**
 * Sets up the ICS module to FEI at approximately 48MHz with the peripheral
 * clock at 24MHz
 */
static void ics_setup(void)
{
    //we assume this is run soon after setup
    ICS->C2 = 0x00; //bdiv=0
    ICS->C1 = 0x04; //internal reference clock to FLL
}

static void api_tick(void)
{
    typedef enum { API_INIT, API_READY, API_ERASE_WAIT, API_PROGRAM_WAIT, API_FINISH, API_ERR } State;
    static State state = API_INIT;

    //state actions
    switch (state)
    {
    default:
        break;
    }

    //transtions
    switch (state)
    {
    case API_INIT:
        //set up fclkdiv for the flash module
        FTMRE->FCLKDIV = 0x17; //divide by 24 to get into the target range
        FlashAPIState.status = API_STATUS_READY_MASK;
        state = API_READY;
        break;
    case API_READY:
        if (!(FlashAPIState.status & API_STATUS_READY_MASK))
        {
            //we are asked to execute a command
            uint8_t cmd = (FlashAPIState.status & API_STATUS_CMD_MASK) >> API_STATUS_CMD_SHIFT;
            switch (cmd)
            {
            case API_STATUS_CMD_ERASE:
                //flash mass erase
                FTMRE->FCCOBIX  = 0;
                FTMRE->FCCOBHI = 0x8;
                FTMRE->FSTAT = FTMRE_FSTAT_CCIF_MASK | FTMRE_FSTAT_ACCERR_MASK | FTMRE_FSTAT_FPVIOL_MASK;
                state = API_ERASE_WAIT;
                break;
            case API_STATUS_CMD_PROGRAM:
                //flash program
                state = API_PROGRAM_WAIT;
                break;
            default:
            FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_NOT_IMPLEMENTED);
                state = API_ERR;
                break;
            }
        }
        break;
    case API_ERASE_WAIT:
        state = API_FINISH; //wait for the command to complete
        break;
    case API_PROGRAM_WAIT:
    FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_NOT_IMPLEMENTED);
        state = API_ERR;
        break;
    case API_FINISH:
        if (FTMRE->FSTAT & FTMRE_FSTAT_CCIF_MASK)
        {
            if (FTMRE->FSTAT & ~(FTMRE_FSTAT_CCIF_MASK))
            {
                //a flash error occurred
                FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_FLASH) | API_STATUS_ERROR(FTMRE->FSTAT);
                state = API_READY;
            }
            else
            {
                FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_OK);
                state = API_READY;
            }
        }
        break;
    default:
        break;
    }
}

int main()
{
    //set up the clock to our known 48MHz frequency
    ics_setup();

#if DEBUG
    SIM->SCGC |= SIM_SCGC_PIT_MASK;
    PIT->MCR = 0;
    PIT->CHANNEL[0].LDVAL = 12000000U;
    PIT->CHANNEL[0].TCTRL = PIT_TCTRL_TIE_MASK;
    PIT->CHANNEL[0].TFLG = 0x1;
    PIT->CHANNEL[0].TCTRL |= PIT_TCTRL_TEN_MASK;
    NVIC->ISER[0] = 1 << 22;
#endif
    __enable_irq();

    //enable GPIO
    GPIOA->PIDR |= 1 << 8;
    GPIOA->PDDR |= 1 << 8;
    GPIOA->PSOR |= 1 << 8;

    while (1)
    {
        api_tick();

        //on every cycle we pet the dog
        //NOTE: We cannot use an interrupt to reset the watchdog.
        //It causes a hard fault or something that cuases the CPU to reset :(
        __disable_irq();
        WDOG->CNT = 0x02A6;
        WDOG->CNT = 0x80B4;
        __enable_irq();

    }

    return 0;
}

#if DEBUG
void PIT_CH0_IRQHandler(void)
{
    PIT->CHANNEL[0].TFLG = 0x1;
    GPIOA->PTOR = 1 << 8;
}
#endif
