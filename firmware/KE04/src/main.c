/**
 * KE04 Loading Firmware
 * Main
 *
 * Kevin Cuzner
 */

#include "MKE04Z4.h"

#define DEBUGREG ((volatile uint32_t*)0x20000200)

/**
 * Sets up the ICS module to FEI at approximately 42MHz
 */
static void ics_setup(void)
{
    ICS->C2 = 0x00; //bdiv=0
    ICS->C1 = 0x04; //internal reference clock to FLL
}

int main()
{
    //set up the clock to our known 42MHz frequency
    ics_setup();

    SIM->SCGC |= SIM_SCGC_PIT_MASK;
    PIT->MCR = 0;
    PIT->CHANNEL[0].LDVAL = 1200000U;
    PIT->CHANNEL[0].TCTRL = PIT_TCTRL_TIE_MASK;
    PIT->CHANNEL[0].TFLG = 0x1;
    PIT->CHANNEL[0].TCTRL |= PIT_TCTRL_TEN_MASK;
    NVIC->ISER[0] = 1 << 22;
    __enable_irq();

    //enable GPIO
    GPIOA->PIDR |= 1 << 8;
    GPIOA->PDDR |= 1 << 8;
    GPIOA->PSOR |= 1 << 8;

    *DEBUGREG = 0xaa5500;

    while (1)
    {
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

void PIT_CH0_IRQHandler(void)
{
    PIT->CHANNEL[0].TFLG = 0x1;
    GPIOA->PTOR = 1 << 8;
}
