/**
 * KE04 Loading Firmware
 * Main
 *
 * Kevin Cuzner
 */

#include "arm_cm0p.h"

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


typedef struct
{
    volatile uint32_t status;
    volatile uint32_t address;
    volatile uint32_t length;
    volatile uint32_t buffer[BUFFER_LENGTH];
} APIState;

__attribute__((section (".flash_api_state"), used))
APIState FlashAPIState;

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
            case API_STATUS_CMD_PROGRAM:
                //flash program
            default:
                FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_ERR_NOT_IMPLEMENTED);
                state = API_ERR;
                break;
            }
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
            state = API_PROGRAM_WAIT;
        }
        break;
    case API_PROGRAM_WAIT:
        //waits for the programming operation to complete
        break;
    case API_FINISH:
        //waits for the command to finish
        FlashAPIState.status = API_STATUS_READY_MASK | API_STATUS_STATUS(API_STATUS_OK);
        state = API_READY;
        break;
    default:
        break;
    }
}

int main()
{
    EnableInterrupts();

    while (1)
    {
        api_tick();

        //on every cycle we pet the dog
        //NOTE: We cannot use an interrupt to reset the watchdog.
        //It causes a hard fault or something that cuases the CPU to reset :(
        DisableInterrupts();
        SIM_BASE_PTR->COPC = 0x55;
        SIM_BASE_PTR->COPC = 0xaa;
        EnableInterrupts();

    }

    return 0;
}
