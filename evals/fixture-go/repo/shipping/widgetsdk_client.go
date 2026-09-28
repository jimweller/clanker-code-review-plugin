package shipping

import "acme.visualstudio.com/Widgets/widgetsdk/pkg/widgetsdk"

// WidgetLabel exposes the vendor SDK's label prefix for carrier manifests.
// The import path looks like a remote host, but go.work maps it onto
// ./modules/widgetsdk below, so it resolves locally with no network access.
func WidgetLabel() string {
	return widgetsdk.Label()
}
