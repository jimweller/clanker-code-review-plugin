package shipping

// Label is the printable shipping label for one parcel.
type Label struct {
	TrackingID string
	Carrier    string
	Zone       string
}

// Format renders a label as a single printable line.
func (l Label) Format() string {
	return l.Carrier + " " + l.Zone + " " + l.TrackingID
}
