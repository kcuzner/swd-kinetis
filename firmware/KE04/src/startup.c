/**
 * KE04 Loading Firmware
 * Mid-level startup code
 *
 * Kevin Cuzner
 */

 /*
  * Linker-provided addresses and values for initial loading
  */

#include <stdint.h>

extern uint32_t _start_bss, _end_bss;

void startup()
{
    /* Zero the BSS */
    uint32_t *dest;
    for (dest = &_start_bss; dest < &_end_bss; dest++)
        *dest = 0;

    main();
}
