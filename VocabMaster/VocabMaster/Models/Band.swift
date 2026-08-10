import SwiftUI

enum Band: Int, CaseIterable, Identifiable, Codable, Hashable {
    case b400 = 400
    case b600 = 600
    case b800 = 800
    case b990 = 990

    var id: Int { rawValue }

    var title: String { "衝 \(rawValue) 分" }

    var subtitle: String {
        switch self {
        case .b400: return "基礎必備單字"
        case .b600: return "進階必備單字"
        case .b800: return "高分必備單字"
        case .b990: return "滿分挑戰單字"
        }
    }

    var color: Color {
        switch self {
        case .b400: return Color(red: 0.53, green: 0.38, blue: 0.25)
        case .b600: return Color(red: 0.42, green: 0.63, blue: 0.38)
        case .b800: return Color(red: 0.35, green: 0.55, blue: 0.82)
        case .b990: return Color(red: 0.85, green: 0.65, blue: 0.13)
        }
    }

    /// Page range (1-100) within the full 1000-word list that belongs to this band.
    var pageRange: ClosedRange<Int> {
        switch self {
        case .b400: return 1...25
        case .b600: return 26...50
        case .b800: return 51...75
        case .b990: return 76...100
        }
    }

    var groupCount: Int { pageRange.count }

    func groupIndex(forPage page: Int) -> Int {
        page - pageRange.lowerBound + 1
    }

    func page(forGroupIndex index: Int) -> Int {
        pageRange.lowerBound + index - 1
    }
}
