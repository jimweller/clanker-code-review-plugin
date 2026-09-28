package warehouse

// StockUpdate is the event this package publishes whenever a SKU's on-hand
// weight changes. Downstream consumers decode it with the "weight" JSON key.
type StockUpdate struct {
	SKU      string  `json:"sku"`
	WeightKG float64 `json:"weight"` // kilograms
}

// PublishStockUpdate builds the event for a weight change, in kilograms.
func PublishStockUpdate(sku string, weightKG float64) StockUpdate {
	return StockUpdate{SKU: sku, WeightKG: weightKG}
}
