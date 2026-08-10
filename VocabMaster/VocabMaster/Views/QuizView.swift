import SwiftUI

private enum QuestionKind {
    case wordToMeaning
    case meaningToWord
}

private struct QuizQuestion: Identifiable {
    let id = UUID()
    let word: VocabWord
    let kind: QuestionKind
    let options: [String]
    let correctIndex: Int
}

private struct QuizAnswer {
    let question: QuizQuestion
    let selectedIndex: Int?
    var isCorrect: Bool { selectedIndex == question.correctIndex }
}

struct QuizView: View {
    let band: Band
    let groupIndex: Int

    @EnvironmentObject private var store: VocabStore
    @StateObject private var speaker = Speaker.shared
    @Environment(\.dismiss) private var dismiss

    @State private var questions: [QuizQuestion] = []
    @State private var currentIndex = 0
    @State private var answers: [QuizAnswer] = []
    @State private var selectedOption: Int?
    @State private var isFinished = false

    var body: some View {
        Group {
            if isFinished {
                QuizResultView(
                    band: band,
                    groupIndex: groupIndex,
                    answers: answers.map { ($0.question.word, $0.question.kind == .wordToMeaning, $0.isCorrect, $0.question.options[$0.question.correctIndex]) },
                    onRetry: startQuiz,
                    onDone: { dismiss() }
                )
            } else if !questions.isEmpty {
                quizBody
            } else {
                ProgressView()
            }
        }
        .navigationTitle("第 \(groupIndex) 組 · 測驗")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            if questions.isEmpty { startQuiz() }
        }
    }

    private var quizBody: some View {
        let question = questions[currentIndex]
        return VStack(spacing: 20) {
            ProgressView(value: Double(currentIndex), total: Double(questions.count))
                .tint(band.color)
                .padding(.horizontal)

            Text("第 \(currentIndex + 1) / \(questions.count) 題")
                .font(.footnote)
                .foregroundStyle(.secondary)

            VStack(spacing: 12) {
                if question.kind == .wordToMeaning {
                    HStack {
                        Text(question.word.word)
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                        Button {
                            speaker.speak(question.word.word)
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                        }
                    }
                    Text("請選出正確的中文意思")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                } else {
                    Text(question.word.meaningOnly)
                        .font(.title2.bold())
                        .multilineTextAlignment(.center)
                    Text("請選出正確的英文單字")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
            .frame(maxWidth: .infinity)
            .background(RoundedRectangle(cornerRadius: 20).fill(Color(.secondarySystemGroupedBackground)))
            .padding(.horizontal)

            VStack(spacing: 10) {
                ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                    optionButton(index: index, option: option, question: question)
                }
            }
            .padding(.horizontal)

            Spacer()

            if selectedOption != nil {
                Button(action: goToNext) {
                    Text(currentIndex == questions.count - 1 ? "完成測驗" : "下一題")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(band.color)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                }
                .padding(.horizontal)
                .padding(.bottom)
            }
        }
        .padding(.top)
    }

    private func optionButton(index: Int, option: String, question: QuizQuestion) -> some View {
        let isSelected = selectedOption == index
        let isCorrect = index == question.correctIndex
        var background: Color = Color(.tertiarySystemGroupedBackground)
        if selectedOption != nil {
            if isCorrect {
                background = .green.opacity(0.25)
            } else if isSelected {
                background = .red.opacity(0.25)
            }
        }

        return Button {
            guard selectedOption == nil else { return }
            selectedOption = index
            answers.append(QuizAnswer(question: question, selectedIndex: index))
        } label: {
            HStack {
                Text(option)
                    .multilineTextAlignment(.leading)
                Spacer()
                if selectedOption != nil && isCorrect {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                } else if isSelected {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                }
            }
            .padding()
            .background(RoundedRectangle(cornerRadius: 12).fill(background))
        }
        .buttonStyle(.plain)
        .disabled(selectedOption != nil)
    }

    private func goToNext() {
        if currentIndex == questions.count - 1 {
            let score = answers.filter { $0.isCorrect }.count
            store.recordQuizScore(band: band, groupIndex: groupIndex, score: score)
            isFinished = true
        } else {
            currentIndex += 1
            selectedOption = nil
        }
    }

    private func startQuiz() {
        let words = store.words(forBand: band, groupIndex: groupIndex)
        questions = words.map { word in
            let kind: QuestionKind = Bool.random() ? .wordToMeaning : .meaningToWord
            let distractors = store.randomDistractors(excluding: word, band: band, count: 3)
            switch kind {
            case .wordToMeaning:
                var options = distractors.map { $0.meaningOnly }
                let correctText = word.meaningOnly
                let correctIndex = Int.random(in: 0...options.count)
                options.insert(correctText, at: correctIndex)
                return QuizQuestion(word: word, kind: kind, options: options, correctIndex: correctIndex)
            case .meaningToWord:
                var options = distractors.map { $0.word }
                let correctIndex = Int.random(in: 0...options.count)
                options.insert(word.word, at: correctIndex)
                return QuizQuestion(word: word, kind: kind, options: options, correctIndex: correctIndex)
            }
        }
        currentIndex = 0
        answers = []
        selectedOption = nil
        isFinished = false
    }
}

private struct QuizResultView: View {
    let band: Band
    let groupIndex: Int
    let answers: [(word: VocabWord, wasWordToMeaning: Bool, isCorrect: Bool, correctAnswer: String)]
    let onRetry: () -> Void
    let onDone: () -> Void

    private var score: Int { answers.filter { $0.isCorrect }.count }

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 8) {
                Text("測驗結果")
                    .font(.title2.bold())
                Text("\(score) / \(answers.count)")
                    .font(.system(size: 48, weight: .bold, design: .rounded))
                    .foregroundStyle(band.color)
                Text(score == answers.count ? "太棒了，全部答對！" : "再複習一下答錯的單字吧")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding()

            List {
                ForEach(Array(answers.enumerated()), id: \.offset) { _, answer in
                    HStack {
                        Image(systemName: answer.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                            .foregroundStyle(answer.isCorrect ? .green : .red)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(answer.word.word).font(.headline)
                            Text(answer.correctAnswer)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .listStyle(.plain)

            HStack(spacing: 12) {
                Button(action: onRetry) {
                    Text("再測一次")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(band.color.opacity(0.15))
                        .foregroundStyle(band.color)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                }
                Button(action: onDone) {
                    Text("返回")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(band.color)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                }
            }
            .padding()
        }
    }
}

#Preview {
    NavigationStack {
        QuizView(band: .b400, groupIndex: 1).environmentObject(VocabStore.shared)
    }
}
