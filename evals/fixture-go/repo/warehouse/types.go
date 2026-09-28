package warehouse

// PriceInfo holds the pricing basis for a SKU. A SKU with no price entry
// yet is represented by a nil *PriceInfo on Stock, not a zero value.
type PriceInfo struct {
	Amount   float64
	Currency string
}

// Stock is one warehouse row: a SKU, its on-hand quantity, and its price.
type Stock struct {
	SKU       string
	Quantity  int
	WarehouseID int
	PriceInfo *PriceInfo
}
