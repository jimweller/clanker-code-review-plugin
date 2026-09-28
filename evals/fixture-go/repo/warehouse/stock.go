package warehouse

// NewStock creates a Stock row for a SKU that has not been priced yet.
// PriceInfo is left nil until a price is loaded from the pricing service.
func NewStock(sku string, quantity int) *Stock {
	return &Stock{SKU: sku, Quantity: quantity}
}

// Price returns the stock's current price amount.
func (s *Stock) Price() float64 {
	return s.PriceInfo.Amount
}

// AdjustQuantity applies a signed delta to the on-hand quantity.
func (s *Stock) AdjustQuantity(delta int) {
	s.Quantity += delta
}
