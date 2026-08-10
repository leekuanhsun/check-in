import SwiftUI

struct BandListView: View {
    @EnvironmentObject private var store: VocabStore

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    header

                    ForEach(Band.allCases) { band in
                        NavigationLink(value: band) {
                            BandCard(band: band, learned: store.learnedCount(forBand: band))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("多益背單字")
            .navigationDestination(for: Band.self) { band in
                GroupListView(band: band)
            }
            .navigationDestination(for: GroupRoute.self) { route in
                GroupDetailView(band: route.band, groupIndex: route.groupIndex)
            }
            .navigationDestination(for: StudyRoute.self) { route in
                FlashcardView(band: route.band, groupIndex: route.groupIndex)
            }
            .navigationDestination(for: QuizRoute.self) { route in
                QuizView(band: route.band, groupIndex: route.groupIndex)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("挑選你的目標分數")
                .font(.title2.bold())
            Text("共 1000 字，依 400 / 600 / 800 / 990 分級距分組，每組 10 字")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct BandCard: View {
    let band: Band
    let learned: Int

    private var total: Int { band.groupCount * 10 }
    private var progress: Double { total == 0 ? 0 : Double(learned) / Double(total) }

    var body: some View {
        HStack(spacing: 16) {
            ZStack {
                Circle()
                    .stroke(band.color.opacity(0.2), lineWidth: 8)
                Circle()
                    .trim(from: 0, to: progress)
                    .stroke(band.color, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                Text("\(Int(progress * 100))%")
                    .font(.caption.bold())
                    .foregroundStyle(band.color)
            }
            .frame(width: 56, height: 56)

            VStack(alignment: .leading, spacing: 4) {
                Text(band.title)
                    .font(.headline)
                Text(band.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text("已學 \(learned)/\(total) 字 · \(band.groupCount) 組")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundStyle(.tertiary)
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 16).fill(Color(.secondarySystemGroupedBackground)))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(band.color.opacity(0.4), lineWidth: 1.5)
        )
    }
}

#Preview {
    BandListView().environmentObject(VocabStore.shared)
}
