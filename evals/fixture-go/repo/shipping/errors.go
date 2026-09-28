package shipping

import "errors"

// ErrNoCarrier is returned when no carrier can service a destination.
var ErrNoCarrier = errors.New("shipping: no carrier available")
