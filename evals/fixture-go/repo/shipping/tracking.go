package shipping

// TrackingEvent is one carrier scan on a parcel's route.
type TrackingEvent struct {
	Code string
	Note string
}

// Describe renders a tracking event for the customer-facing timeline.
func (e TrackingEvent) Describe() string {
	return e.Code + ": " + e.Note
}
