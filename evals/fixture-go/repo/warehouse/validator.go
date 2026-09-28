package warehouse

// ValidQuantity reports whether q is an acceptable on-hand quantity.
func ValidQuantity(q int) bool {
	return q >= 0 && q <= 1_000_000
}
