package warehouse

// ApplyDiscount returns price reduced by pct (0 to 1). Callers pass the
// customer tier discount loaded from config. There is no test anywhere in
// this repository covering zero quantity, a negative pct, or pct >= 1.
func ApplyDiscount(price float64, pct float64) float64 {
	return price * (1 - pct)
}
