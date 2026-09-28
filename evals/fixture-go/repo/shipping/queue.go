package shipping

// PendingLabels holds label jobs waiting to be printed.
type PendingLabels struct {
	items []Label
}

// Push queues a label for printing.
func (q *PendingLabels) Push(l Label) {
	q.items = append(q.items, l)
}

// Len reports how many labels are queued.
func (q *PendingLabels) Len() int {
	return len(q.items)
}
