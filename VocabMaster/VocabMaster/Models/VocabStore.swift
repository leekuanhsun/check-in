import Foundation
import Combine

struct QuizResult: Codable, Hashable {
    var bestScore: Int
    var attempts: Int
}

final class VocabStore: ObservableObject {
    static let shared = VocabStore()

    @Published private(set) var allWords: [VocabWord] = []
    @Published private(set) var learnedWordIDs: Set<String> = []
    @Published private(set) var quizResults: [String: QuizResult] = [:]

    private let wordsByPage: [Int: [VocabWord]]
    private let wordsByBand: [Int: [VocabWord]]

    private let learnedKey = "vocab.learnedWordIDs"
    private let quizKey = "vocab.quizResults"

    private init() {
        let loaded = VocabStore.loadWords()
        allWords = loaded
        wordsByPage = Dictionary(grouping: loaded, by: { $0.page })
        wordsByBand = Dictionary(grouping: loaded, by: { $0.band })
        loadProgress()
    }

    private static func loadWords() -> [VocabWord] {
        guard let url = Bundle.main.url(forResource: "vocab", withExtension: "json") else {
            assertionFailure("vocab.json not found in bundle")
            return []
        }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode([VocabWord].self, from: data)
        } catch {
            assertionFailure("Failed to decode vocab.json: \(error)")
            return []
        }
    }

    // MARK: - Query helpers

    func words(forBand band: Band) -> [VocabWord] {
        (wordsByBand[band.rawValue] ?? []).sorted { $0.page < $1.page }
    }

    func words(forPage page: Int) -> [VocabWord] {
        wordsByPage[page] ?? []
    }

    func words(forBand band: Band, groupIndex: Int) -> [VocabWord] {
        words(forPage: band.page(forGroupIndex: groupIndex))
    }

    func randomDistractors(excluding word: VocabWord, band: Band, count: Int) -> [VocabWord] {
        let pool = (wordsByBand[band.rawValue] ?? []).filter { $0.id != word.id }
        return Array(pool.shuffled().prefix(count))
    }

    // MARK: - Progress: learned words

    func isLearned(_ word: VocabWord) -> Bool {
        learnedWordIDs.contains(word.id)
    }

    func toggleLearned(_ word: VocabWord) {
        if learnedWordIDs.contains(word.id) {
            learnedWordIDs.remove(word.id)
        } else {
            learnedWordIDs.insert(word.id)
        }
        persistLearned()
    }

    func setLearned(_ word: VocabWord, learned: Bool) {
        if learned {
            learnedWordIDs.insert(word.id)
        } else {
            learnedWordIDs.remove(word.id)
        }
        persistLearned()
    }

    func learnedCount(forBand band: Band) -> Int {
        (wordsByBand[band.rawValue] ?? []).filter { learnedWordIDs.contains($0.id) }.count
    }

    func learnedCount(forPage page: Int) -> Int {
        (wordsByPage[page] ?? []).filter { learnedWordIDs.contains($0.id) }.count
    }

    // MARK: - Progress: quiz results

    private func groupKey(band: Band, groupIndex: Int) -> String {
        "\(band.rawValue)_\(groupIndex)"
    }

    func quizResult(band: Band, groupIndex: Int) -> QuizResult? {
        quizResults[groupKey(band: band, groupIndex: groupIndex)]
    }

    func recordQuizScore(band: Band, groupIndex: Int, score: Int) {
        let key = groupKey(band: band, groupIndex: groupIndex)
        var result = quizResults[key] ?? QuizResult(bestScore: 0, attempts: 0)
        result.bestScore = max(result.bestScore, score)
        result.attempts += 1
        quizResults[key] = result
        persistQuiz()
    }

    // MARK: - Persistence

    private func persistLearned() {
        let array = Array(learnedWordIDs)
        if let data = try? JSONEncoder().encode(array) {
            UserDefaults.standard.set(data, forKey: learnedKey)
        }
    }

    private func persistQuiz() {
        if let data = try? JSONEncoder().encode(quizResults) {
            UserDefaults.standard.set(data, forKey: quizKey)
        }
    }

    private func loadProgress() {
        if let data = UserDefaults.standard.data(forKey: learnedKey),
           let array = try? JSONDecoder().decode([String].self, from: data) {
            learnedWordIDs = Set(array)
        }
        if let data = UserDefaults.standard.data(forKey: quizKey),
           let dict = try? JSONDecoder().decode([String: QuizResult].self, from: data) {
            quizResults = dict
        }
    }
}
