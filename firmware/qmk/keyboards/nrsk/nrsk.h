#pragma once
#include "quantum.h"

// Called once per detent of a corner thumbwheel (index 0 = left half, 1 = right half);
// clockwise = turned clockwise seen from above.
bool dial_update_user(uint8_t index, bool clockwise);
