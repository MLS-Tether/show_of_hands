import { jsPDF } from 'jspdf'
import { formatPercent } from './format'

export function buildReportCardPdf({ student, grades }) {
  const doc = new jsPDF()

  doc.setFontSize(18)
  doc.text('Report Card', 14, 20)

  doc.setFontSize(12)
  doc.text(`Student: ${student.username}`, 14, 32)

  let y = 48
  doc.setFontSize(11)
  doc.text('Section', 14, y)
  doc.text('Period', 100, y)
  doc.text('Grade', 140, y)
  doc.text('Letter', 170, y)
  y += 4
  doc.line(14, y, 196, y)
  y += 8

  grades.forEach((g) => {
    doc.text(g.class_name, 14, y)
    doc.text(String(g.period), 100, y)
    doc.text(g.percentage != null ? formatPercent(g.percentage) : '—', 140, y)
    doc.text(g.letter_grade || '—', 170, y)
    y += 8
  })

  return doc
}

export function downloadReportCard(student, grades) {
  buildReportCardPdf({ student, grades }).save(`${student.username}-report-card.pdf`)
}

export function printReportCard(student, grades) {
  const doc = buildReportCardPdf({ student, grades })
  doc.autoPrint()
  window.open(doc.output('bloburl'), '_blank')
}
