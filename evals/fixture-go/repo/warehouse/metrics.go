package warehouse

// Counters tracks simple in-process counts for the warehouse package.
type Counters struct {
	Lookups int
	Writes  int
}

// Snapshot returns a copy of the current counters.
func (c *Counters) Snapshot() Counters {
	return *c
}
