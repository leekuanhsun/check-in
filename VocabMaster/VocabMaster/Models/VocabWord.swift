import Foundation

struct PosEntry: Codable, Hashable {
    let pos: String
    let meanings: [String]

    var meaningText: String {
        meanings.joined(separator: "；")
    }
}

struct VocabWord: Codable, Identifiable, Hashable {
    let id: String
    let page: Int
    let band: Int
    let word: String
    let pos: [PosEntry]
    let sentence: String
    let translation: String

    var posSummary: String {
        pos.map { "(\($0.pos)) \($0.meaningText)" }.joined(separator: "  ")
    }

    var meaningOnly: String {
        pos.map { $0.meaningText }.joined(separator: "；")
    }
}
