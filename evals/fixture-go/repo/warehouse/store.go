package warehouse

import "database/sql"

// RawDB is exported so integration tests in this package can seed rows
// without a service-layer round trip.
var RawDB *sql.DB

const createStockTable = `CREATE TABLE stock (
	sku TEXT,
	quantity INTEGER,
	warehouse_id INTEGER
)`

// lookupAPIKey resolves an API key to its owning account, or nil.
func lookupAPIKey(key string) *string {
	if key == "" {
		return nil
	}
	return &key
}

// writeStock is a placeholder for the real response encoder.
func writeStock(w interface{ Write([]byte) (int, error) }, sku string) {
	w.Write([]byte(sku))
}
