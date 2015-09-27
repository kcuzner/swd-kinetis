# Firmware makefile for KE04
#
# Kevin Cuzner

PROJECT=firmware

# Structure
BINDIR=bin
OBJDIR=obj
INCDIR=include
SRCDIR=src

# Target CPU
CPU=cortex-m0plus

# Linker script
LSCRIPT=firmware.ld

# Sources
SRC=$(wildcard $(SRCDIR)/*.c)
ASM=$(wildcard $(SRCDIR)/*.S)

# Includes
INCLUDE=-I$(INCDIR)

# C Flags
GCFLAGS  = -Wall -fno-common -mthumb -ffreestanding -fno-builtin -nodefaultlibs\
 	-nostdlib -mcpu=$(CPU) -Os -Wa,-ahlms=$(addprefix $(OBJDIR)/,$(notdir $(<:.c=.lst))) -g
GCFLAGS += $(INCLUDE)
LDFLAGS += -nostartfiles -T$(LSCRIPT) -mthumb -mcpu=$(CPU) -Wl,-Map=$(BINDIR)/$(PROJECT).map
ASFLAGS += -mcpu=$(CPU)

# Tools
CC = arm-none-eabi-gcc
AS = arm-none-eabi-as
AR = arm-none-eabi-ar
LD = arm-none-eabi-ld
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size
OBJDUMP = arm-none-eabi-objdump

RM = rm -rf

## Build process

OBJ := $(addprefix $(OBJDIR)/,$(notdir $(SRC:.c=.o)))
OBJ += $(addprefix $(OBJDIR)/,$(notdir $(ASM:.S=.o)))

all:: $(BINDIR)/$(PROJECT).hex

list: $(BINDIR)/$(PROJECT).elf
	$(OBJDUMP) -D $(BINDIR)/$(PROJECT).elf > $(BINDIR)/$(PROJECT).lst

size: $(BINDIR)/$(PROJECT).elf
	$(SIZE) $(BINDIR)/$(PROJECT).elf

$(BINDIR)/$(PROJECT).hex: $(BINDIR)/$(PROJECT).elf
	$(OBJCOPY) -R .stack -O ihex $(BINDIR)/$(PROJECT).elf $(BINDIR)/$(PROJECT).hex

$(BINDIR)/$(PROJECT).elf: $(LSCRIPT) $(OBJ)
	@mkdir -p $(dir $@)
	$(CC) $(OBJ) $(LDFLAGS) -o $(BINDIR)/$(PROJECT).elf

clean:
	$(RM) $(BINDIR)
	$(RM) $(OBJDIR)

# Compilation
$(OBJDIR)/%.o: $(SRCDIR)/%.c
	@mkdir -p $(dir $@)
	$(CC) $(GCFLAGS) -c $< -o $@

$(OBJDIR)/%.o: $(SRCDIR)/%.S
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -o $@ $<
