package shipping

// FedExClient calls the FedEx rate API directly.
type FedExClient struct {
	Endpoint string
}

// Quote returns FedEx's quoted rate for a shipment.
func (c *FedExClient) Quote(weightGrams float64) float64 {
	return weightGrams * 0.0039
}

// RateCalculator prices a shipment. It is built around FedExClient
// specifically: adding a second carrier means editing RateCalculator's
// fields and every method on it, rather than passing in a new implementation.
type RateCalculator struct {
	fedex *FedExClient
}

// NewRateCalculator builds a calculator against the FedEx endpoint.
func NewRateCalculator(endpoint string) *RateCalculator {
	return &RateCalculator{fedex: &FedExClient{Endpoint: endpoint}}
}

// Quote prices a shipment through the fixed FedEx client.
func (r *RateCalculator) Quote(weightGrams float64) float64 {
	return r.fedex.Quote(weightGrams)
}
