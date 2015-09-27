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

#define FCMD_START { FTMRE->FSTAT = FTMRE_FSTAT_CCIF_MASK | FTMRE_FSTAT_ACCERR_MASK | FTMRE_FSTAT_FPVIOL_MASK; }
#define FCMD_MERASE 0x8
#define FCMD_PROG   0x6


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

/**
 * Checks the done state of the FTMRE
 * @return  <0 if there is an error, 0 if not ready, or 1 if ready without error
 */
static int32_t ftmre_is_done(void)
{
    if (FTMRE->FSTAT & FTMRE_FSTAT_CCIF_MASK)
    {
        if (FTMRE->FSTAT & ~(FTMRE_FSTAT_CCIF_MASK))
        {
            //there were errors
            return -1;

        }
        else
        {
            //nothing but the ccif is active...no errors
            return 1;
        }
    }

    return 0;
}

static void api_tick(void)
{
    typedef enum { API_INIT, API_READY, API_PROGRAM_LOAD, API_PROGRAM_WAIT, API_FINISH, API_ERR } State;
    static State state = API_INIT;
    static uint32_t current_index;

    uint32_t temp;

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
#if DEBUG
            GPIOA->PCOR |= 1 << 8;
#endif
            //we are asked to execute a command
            uint8_t cmd = (FlashAPIState.status & API_STATUS_CMD_MASK) >> API_STATUS_CMD_SHIFT;
            switch (cmd)
            {
            case API_STATUS_CMD_ERASE:
                //flash mass erase
                FTMRE->FCCOBIX = 0;
                FTMRE->FCCOBHI = FCMD_MERASE;
                FCMD_START;
                state = API_FINISH;
                break;
            case API_STATUS_CMD_PROGRAM:
                //flash program
                current_index = 0;
                state = API_PROGRAM_LOAD;
                break;
            default:
            FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_NOT_IMPLEMENTED);
                state = API_ERR;
                break;
            }
        }
        else
        {
#if DEBUG
            GPIOA->PSOR |= 1 << 8;
#endif
        }
        break;
    case API_PROGRAM_LOAD:
        //loads the command for the current byte into the flash to be programmed
        //If we are at the end of the buffer, this calls API_FINISH
        if (current_index >= FlashAPIState.length)
        {
            state = API_FINISH;
        }
        else
        {
            temp = FlashAPIState.address + (current_index & 0xFE) * 4;
            //command setup
            FTMRE->FCCOBIX = 0x0;
            FTMRE->FCCOBHI = FCMD_PROG;
            FTMRE->FCCOBLO = (temp & 0xFF0000) >> 16;
            FTMRE->FCCOBIX = 0x1;
            FTMRE->FCCOBHI = (temp & 0xFF00) >> 8;
            FTMRE->FCCOBLO = (temp & 0xFF);
            //data setup
            temp = FlashAPIState.buffer[current_index & 0xFE];
            FTMRE->FCCOBIX = 0x2;
            FTMRE->FCCOBHI = (temp & 0xFF00) >> 8;
            FTMRE->FCCOBLO = (temp & 0xFF);
            FTMRE->FCCOBIX = 0x3;
            FTMRE->FCCOBHI = (temp) >> 24;
            FTMRE->FCCOBLO = (temp & 0xFF0000) >> 16;
            temp = FlashAPIState.buffer[(current_index & 0xFE) + 1];
            FTMRE->FCCOBIX = 0x4;
            FTMRE->FCCOBHI = (temp & 0xFF00) >> 8;
            FTMRE->FCCOBLO = (temp & 0xFF);
            FTMRE->FCCOBIX = 0x5;
            FTMRE->FCCOBHI = (temp) >> 24;
            FTMRE->FCCOBLO = (temp & 0xFF0000) >> 16;
            //start command
            FCMD_START;
            state = API_PROGRAM_WAIT;
        }
        break;
    case API_PROGRAM_WAIT:
        //waits for the programming operation to complete
        temp = ftmre_is_done();
        if (temp < 0)
        {
            //a flash error occurred
            FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_FLASH) | API_STATUS_ERROR(FTMRE->FSTAT);
            state = API_READY;
        }
        else if (temp > 0)
        {
            current_index += 2; //we just programmed 2 4-byte longwords
            state = API_PROGRAM_LOAD;
        }
        break;
    case API_FINISH:
        //waits for the command to finish
        temp = ftmre_is_done();
        if (temp < 0)
        {
            //a flash error occurred
            FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_FLASH) | API_STATUS_ERROR(FTMRE->FSTAT);
            state = API_READY;
        }
        else if (temp > 0)
        {
            FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_OK);
            state = API_READY;
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
    //enable GPIO
    GPIOA->PIDR |= 1 << 8;
    GPIOA->PDDR |= 1 << 8;
    GPIOA->PSOR |= 1 << 8;

    SIM->SCGC |= SIM_SCGC_PIT_MASK;
    PIT->MCR = 0;
    PIT->CHANNEL[0].LDVAL = 12000000U;
    PIT->CHANNEL[0].TCTRL = PIT_TCTRL_TIE_MASK;
    PIT->CHANNEL[0].TFLG = 0x1;
    PIT->CHANNEL[0].TCTRL |= PIT_TCTRL_TEN_MASK;
    NVIC->ISER[0] = 1 << 22;
#endif
    __enable_irq();



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
