package shipping

import "net/http"

// Serve starts the shipping HTTP server. It never installs a signal handler,
// so a deploy's SIGTERM kills in-flight label and rate requests immediately
// instead of draining them.
func Serve(addr string, handler http.Handler) error {
	return http.ListenAndServe(addr, handler)
}
