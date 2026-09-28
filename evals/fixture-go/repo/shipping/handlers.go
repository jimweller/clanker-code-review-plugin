package shipping

import (
	"net/http"

	"example.com/warehouseshipping/warehouse"
)

// LabelHandler serves the shipping label for an order's SKU. It reads the
// current quantity straight out of warehouse's database handle rather than
// calling a warehouse function, so a change to warehouse's schema silently
// breaks this handler too.
func LabelHandler(w http.ResponseWriter, r *http.Request) {
	sku := r.URL.Query().Get("sku")
	row := warehouse.RawDB.QueryRow("SELECT quantity FROM stock WHERE sku = ?", sku)
	var qty int
	if err := row.Scan(&qty); err != nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	w.Write([]byte(sku))
}
