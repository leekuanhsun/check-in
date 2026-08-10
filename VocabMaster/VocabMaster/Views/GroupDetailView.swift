import SwiftUI

struct GroupDetailView: View {
    let band: Band
    let groupIndex: Int

    @EnvironmentObject private var store: VocabStore
    @StateObject private var speaker = Speaker.shared

    private var words: [VocabWord] {
        store.words(forBand: band, groupIndex: groupIndex)
    }

    var body: some View {
        List {
            Section {
                HStack(spacing: 12) {
                    NavigationLink(value: StudyRoute(band: band, groupIndex: groupIndex)) {
                        actionLabel(title: "開始學習", icon: "rectangle.on.rectangle", color: band.color)
                    }
                    NavigationLink(value: QuizRoute(band: band, groupIndex: groupIndex)) {
                        actionLabel(title: "單字測驗", icon: "checkmark.circle", color: band.color)
                    }
                }
                .buttonStyle(.plain)
                .listRowInsets(EdgeInsets())
                .listRowBackground(Color.clear)
                .padding(.vertical, 4)
            }

            Section("本組單字 (\(words.count))") {
                ForEach(words) { word in
                    WordRow(word: word, speaker: speaker)
                }
            }
        }
        .navigationTitle("第 \(groupIndex) 組")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func actionLabel(title: String, icon: String, color: Color) -> some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
            Text(title)
                .font(.subheadline.bold())
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 14)
        .background(RoundedRectangle(cornerRadius: 14).fill(color))
        .foregroundStyle(.white)
    }
}

struct StudyRoute: Hashable {
    let band: Band
    let groupIndex: Int
}

struct QuizRoute: Hashable {
    let band: Band
    let groupIndex: Int
}

private struct WordRow: View {
    let word: VocabWord
    @ObservedObject var speaker: Speaker
    @EnvironmentObject private var store: VocabStore

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Button {
                speaker.speak(word.word)
            } label: {
                Image(systemName: "speaker.wave.2.fill")
                    .foregroundStyle(.blue)
            }
            .buttonStyle(.plain)
            .padding(.top, 2)

            VStack(alignment: .leading, spacing: 2) {
                Text(word.word)
                    .font(.headline)
                Text(word.posSummary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            if store.isLearned(word) {
                Image(systemName: "checkmark.seal.fill")
                    .foregroundStyle(.green)
            }
        }
        .padding(.vertical, 2)
    }
}
