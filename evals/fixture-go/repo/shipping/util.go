package shipping

import "strings"

// NormalizeZone upper-cases and trims a zone code for lookup.
func NormalizeZone(code string) string {
	return strings.ToUpper(strings.TrimSpace(code))
}
