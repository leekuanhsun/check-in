import SwiftUI

struct GroupListView: View {
    let band: Band
    @EnvironmentObject private var store: VocabStore

    private let columns = [GridItem(.adaptive(minimum: 84), spacing: 12)]

    var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(1...band.groupCount, id: \.self) { index in
                    NavigationLink(value: GroupRoute(band: band, groupIndex: index)) {
                        GroupCell(band: band, groupIndex: index,
                                  learned: store.learnedCount(forPage: band.page(forGroupIndex: index)),
                                  quiz: store.quizResult(band: band, groupIndex: index))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle(band.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct GroupRoute: Hashable {
    let band: Band
    let groupIndex: Int
}

private struct GroupCell: View {
    let band: Band
    let groupIndex: Int
    let learned: Int
    let quiz: QuizResult?

    var body: some View {
        VStack(spacing: 6) {
            ZStack {
                Circle()
                    .fill(learned == 10 ? band.color : band.color.opacity(0.15))
                Text("\(groupIndex)")
                    .font(.headline)
                    .foregroundStyle(learned == 10 ? .white : band.color)
            }
            .frame(width: 48, height: 48)

            Text("第 \(groupIndex) 組")
                .font(.caption2)
                .foregroundStyle(.secondary)

            if let quiz {
                Text("測驗 \(quiz.bestScore)/10")
                    .font(.caption2.bold())
                    .foregroundStyle(band.color)
            } else {
                Text("\(learned)/10")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(.secondarySystemGroupedBackground)))
    }
}

#Preview {
    NavigationStack {
        GroupListView(band: .b400).environmentObject(VocabStore.shared)
    }
}
