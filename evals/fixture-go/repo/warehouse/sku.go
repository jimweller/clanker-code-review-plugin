package warehouse

import "regexp"

var skuPattern = regexp.MustCompile(`^[A-Z]{2}-[0-9]{4,8}$`)

// ValidSKU reports whether sku matches the warehouse's SKU format.
func ValidSKU(sku string) bool {
	return skuPattern.MatchString(sku)
}
