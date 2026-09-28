package warehouse

import "log"

// LogAccess records who touched a SKU and when, for the compliance trail.
func LogAccess(actor, sku, action string) {
	log.Printf("warehouse access actor=%s sku=%s action=%s", actor, sku, action)
}
