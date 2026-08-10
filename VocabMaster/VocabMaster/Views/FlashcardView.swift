import SwiftUI

struct FlashcardView: View {
    let band: Band
    let groupIndex: Int

    @EnvironmentObject private var store: VocabStore
    @StateObject private var speaker = Speaker.shared
    @State private var currentIndex = 0

    private var words: [VocabWord] {
        store.words(forBand: band, groupIndex: groupIndex)
    }

    var body: some View {
        VStack(spacing: 16) {
            progressBar

            TabView(selection: $currentIndex) {
                ForEach(Array(words.enumerated()), id: \.offset) { index, word in
                    FlashcardFace(word: word, band: band, speaker: speaker)
                        .padding(.horizontal)
                        .tag(index)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .never))

            HStack {
                Button {
                    withAnimation { currentIndex = max(0, currentIndex - 1) }
                } label: {
                    Label("上一個", systemImage: "chevron.left")
                }
                .disabled(currentIndex == 0)

                Spacer()

                Text("\(currentIndex + 1) / \(words.count)")
                    .font(.footnote)
                    .foregroundStyle(.secondary)

                Spacer()

                Button {
                    withAnimation { currentIndex = min(words.count - 1, currentIndex + 1) }
                } label: {
                    Label("下一個", systemImage: "chevron.right")
                        .labelStyle(.trailingIcon)
                }
                .disabled(currentIndex == words.count - 1)
            }
            .padding(.horizontal)
            .padding(.bottom)
        }
        .navigationTitle("第 \(groupIndex) 組 · 學習")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                NavigationLink(value: QuizRoute(band: band, groupIndex: groupIndex)) {
                    Text("去測驗")
                }
            }
        }
        .onDisappear { speaker.stop() }
    }

    private var progressBar: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(band.color.opacity(0.15))
                Capsule().fill(band.color)
                    .frame(width: geo.size.width * CGFloat(currentIndex + 1) / CGFloat(max(words.count, 1)))
            }
        }
        .frame(height: 6)
        .padding(.horizontal)
        .padding(.top, 8)
    }
}

private struct FlashcardFace: View {
    let word: VocabWord
    let band: Band
    @ObservedObject var speaker: Speaker
    @EnvironmentObject private var store: VocabStore
    @State private var isFlipped = false

    var body: some View {
        VStack {
            ZStack {
                RoundedRectangle(cornerRadius: 24)
                    .fill(Color(.secondarySystemGroupedBackground))
                    .shadow(color: .black.opacity(0.08), radius: 10, y: 4)

                if isFlipped {
                    backContent
                } else {
                    frontContent
                }
            }
            .onTapGesture {
                withAnimation(.easeInOut(duration: 0.3)) { isFlipped.toggle() }
            }

            HStack(spacing: 24) {
                Button {
                    store.toggleLearned(word)
                } label: {
                    Label(store.isLearned(word) ? "已熟記" : "標記熟記",
                          systemImage: store.isLearned(word) ? "checkmark.seal.fill" : "checkmark.seal")
                }
                .tint(store.isLearned(word) ? .green : .secondary)

                Button {
                    speaker.speak(isFlipped ? word.sentence : word.word)
                } label: {
                    Label("發音", systemImage: "speaker.wave.2.fill")
                }
                .tint(band.color)
            }
            .buttonStyle(.bordered)
            .padding(.top, 12)
        }
    }

    private var frontContent: some View {
        VStack(spacing: 16) {
            Text(word.word)
                .font(.system(size: 40, weight: .bold, design: .rounded))
                .multilineTextAlignment(.center)
                .minimumScaleFactor(0.5)
            Text(word.pos.map { $0.pos }.joined(separator: ", "))
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("點一下卡片看解釋")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .padding()
    }

    private var backContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(word.word)
                    .font(.title.bold())

                ForEach(Array(word.pos.enumerated()), id: \.offset) { _, entry in
                    HStack(alignment: .top, spacing: 6) {
                        Text("(\(entry.pos))")
                            .font(.subheadline.bold())
                            .foregroundStyle(band.color)
                        Text(entry.meaningText)
                            .font(.subheadline)
                    }
                }

                Divider()

                VStack(alignment: .leading, spacing: 6) {
                    Text(word.sentence)
                        .font(.body)
                    Text(word.translation)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct TrailingIconLabelStyle: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack {
            configuration.title
            configuration.icon
        }
    }
}

private extension LabelStyle where Self == TrailingIconLabelStyle {
    static var trailingIcon: TrailingIconLabelStyle { TrailingIconLabelStyle() }
}

#Preview {
    NavigationStack {
        FlashcardView(band: .b400, groupIndex: 1).environmentObject(VocabStore.shared)
    }
}
