package warehouse

// LoadMany fetches the current row for every sku in skus. It queries the
// database once per SKU rather than in a single batched statement.
func LoadMany(skus []string) []*Stock {
	out := make([]*Stock, 0, len(skus))
	for _, sku := range skus {
		row := RawDB.QueryRow("SELECT sku, quantity, warehouse_id FROM stock WHERE sku = ?", sku)
		var s Stock
		if err := row.Scan(&s.SKU, &s.Quantity, &s.WarehouseID); err == nil {
			out = append(out, &s)
		}
	}
	return out
}
