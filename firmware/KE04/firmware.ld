/**
 * Linker script for the KE04 device
 */

OUTPUT_FORMAT("elf32-littlearm", "elf32-littlearm", "elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(_startup)

/**
 * KE04 Reference Manual 3.7.3.2 & Table 4-1
 * "The on-chip SRAM is split into two ranges; 1/4 is allocated to SRAM_L and 3/4 is allocated to SRAM_U."
 *
 * All KE04 devices have 1KB of RAM
 */
MEMORY
{
    sram(WX) : ORIGIN = 0x1FFFFF00, LENGTH = 1K
}

/**
 * The top of the stack is the end of SRAM
 */
TOTAL_RESERVED_STACK = 128; /* On a system with 64K ram, we saw 8K used */
_top_stack = (0x1fffff00+1K);

EXTERN(__interrupt_vector_table);

SECTIONS
{
    .all :
    {
        __interrupt_vector_table = .;
        *(.interrupt_vector_table)
        *(.unsecured_config)
        . = ALIGN(4);
        *(.startup)
        /* Rest of the code */
        *(.text)
        *(.text.*)
        *(.glue_7)
        *(.glue_7t)
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        *(.data)
        *(.data.*)
        *(.shdata)
        . = ALIGN(4);
        *(.flash_api_state)
        . = ALIGN(4);
        _start_bss = .;
        *(.bss)
        *(.bss.*)
        _end_bss = .;

    } > sram

    _bss_size = _end_bss - _start_bss;

    _start_stack = _top_stack - TOTAL_RESERVED_STACK;
    _top_stack = _top_stack;			/* just to make the map file easier to read */
}
