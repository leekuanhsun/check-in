import SwiftUI

@main
struct VocabMasterApp: App {
    var body: some Scene {
        WindowGroup {
            BandListView()
                .environmentObject(VocabStore.shared)
        }
    }
}
