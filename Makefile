# NumChess — chess for the NumWorks calculator.
#   make          build output/chess.nwa
#   make run      install on a connected calculator
#   make check    link the app like the calculator does (output/chess.bin)
#   make test     run engine tests on the host
Q ?= @
CC = arm-none-eabi-gcc
NWLINK = npx --yes -- nwlink@1.0.0
BUILD_DIR = output
SRC = src/main.c src/chess.c src/libc.c

CFLAGS = -std=c99 $(shell $(NWLINK) eadk-cflags-device)
CFLAGS += -Os -Wall -fno-math-errno -fno-tree-loop-distribute-patterns -fno-reorder-functions -flto-partition=one
CFLAGS += -flto -fno-fat-lto-objects -fwhole-program -fvisibility=internal
LDFLAGS = -Wl,--relocatable -nostartfiles --specs=nano.specs
LDFLAGS += -Wl,-e,main -Wl,-u,eadk_app_name -Wl,-u,eadk_app_icon -Wl,-u,eadk_api_level
LDFLAGS += -Wl,--gc-sections -flinker-output=nolto-rel

.PHONY: build run check test clean
build: $(BUILD_DIR)/chess.nwa

run: $(BUILD_DIR)/chess.nwa
	@echo "INSTALL $<"
	$(Q) $(NWLINK) install-nwa $<

check: $(BUILD_DIR)/chess.nwa
	$(Q) $(NWLINK) nwa-bin $< $(BUILD_DIR)/chess.bin
	@echo "BIN     $(BUILD_DIR)/chess.bin: $$(wc -c < $(BUILD_DIR)/chess.bin) bytes"

$(BUILD_DIR)/chess.nwa: $(SRC) src/chess.h src/sprites.h $(BUILD_DIR)/icon.o
	@echo "LD      $@"
	$(Q) $(CC) $(CFLAGS) $(LDFLAGS) $(SRC) $(BUILD_DIR)/icon.o -o $@
	$(Q) arm-none-eabi-strip --strip-unneeded $@
	$(Q) arm-none-eabi-size $@

$(BUILD_DIR)/icon.o: src/icon.png | $(BUILD_DIR)
	@echo "ICON    $<"
	$(Q) $(NWLINK) png-icon-o $< $@

$(BUILD_DIR):
	$(Q) mkdir -p $@

test: | $(BUILD_DIR)
	$(Q) cc -O2 -DPLATFORM_DEVICE=1 $(shell $(NWLINK) eadk-cflags-simulator) test/perft.c -o $(BUILD_DIR)/perft
	$(Q) $(BUILD_DIR)/perft

clean:
	$(Q) rm -rf $(BUILD_DIR)
