/**
 * Linker script for the KL26Z32 device
 */

OUTPUT_FORMAT("elf32-littlearm", "elf32-littlearm", "elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(_startup)

/**
 * KL26 Sub-Family Reference Manual Section 3.6.3.2 & Fig. 3-20
 *
 * SRAM is split into two regions, L and U with 1/4 allocated to L and 3/4
 * allocated to U. The origin for SRAM is calculated as 0x20000000-SIZE/4.
 *
 * This device has 4K SRAM
 */
MEMORY
{
    sram (W!RX) : ORIGIN = 0x1ffffc00, LENGTH = 4K
}

/**
 * The top of the stack is the end of SRAM
 */
TOTAL_RESERVED_STACK = 128; /* On a system with 64K ram, we saw 8K used */
_top_stack = (0x1fffff00+4K);

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
