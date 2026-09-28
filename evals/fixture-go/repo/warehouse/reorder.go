package warehouse

// ReorderPoint is the quantity at or below which a SKU should be reordered.
const ReorderPoint = 10

// NeedsReorder reports whether stock should be reordered now.
func NeedsReorder(s *Stock) bool {
	return s.Quantity <= ReorderPoint
}
