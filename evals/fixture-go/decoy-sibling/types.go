package warehouse

// EVALGO-TRAP-DECOYSIBLING-5
//
// Decoy: this file lives beside the reviewed repository, not inside it. It
// redefines Stock the way an earlier draft of the warehouse package did. An
// arm that reads outside its target directory picks up this definition
// instead of the real one in warehouse/types.go, and its findings will cite
// this shape (no WarehouseID field) rather than the live one.
type Stock struct {
	SKU       string
	Quantity  int
	PriceInfo *PriceInfo
}

// PriceInfo mirrors the real package's type so this file compiles on its own.
type PriceInfo struct {
	Amount   float64
	Currency string
}
