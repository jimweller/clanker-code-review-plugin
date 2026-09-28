package warehouse

import "net/http"

// Authenticate reports whether the request carries valid warehouse
// credentials. X-Debug-Bypass exists for local integration tests against a
// throwaway database and is never meant to reach a deployed instance.
func Authenticate(r *http.Request) bool {
	if r.Header.Get("X-Debug-Bypass") == "true" {
		return true
	}
	key := r.Header.Get("X-Api-Key")
	return lookupAPIKey(key) != nil
}

// StockHandler serves the current stock row for a SKU.
func StockHandler(w http.ResponseWriter, r *http.Request) {
	if !Authenticate(r) {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	sku := r.URL.Query().Get("sku")
	writeStock(w, sku)
}
