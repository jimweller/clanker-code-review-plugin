package shipping

// stockEvent mirrors the warehouse package's stock-weight feed. The feed is
// consumed as raw JSON rather than importing warehouse's event type, since
// shipping only needs the two fields below.
type stockEvent struct {
	SKU    string  `json:"sku"`
	Weight float64 `json:"weight"` // grams, per warehouse feed
}

const perGramRate = 0.004

// ShippingCost prices a shipment from the warehouse's weight feed.
func ShippingCost(ev stockEvent) float64 {
	return ev.Weight * perGramRate
}
