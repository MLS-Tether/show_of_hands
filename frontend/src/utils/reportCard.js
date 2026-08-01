import { jsPDF } from 'jspdf'
import { formatPercent } from './format'

const KIND_LABELS = {
  assignment: 'Assignment',
  quest: 'Quest',
}

const PAGE_BOTTOM_MARGIN = 280

export function buildReportCardPdf({ student, reportCard }) {
  const doc = new jsPDF()

  doc.setFontSize(18)
  doc.text('Report Card', 14, 20)

  doc.setFontSize(12)
  doc.text(`Student: ${student.full_name}`, 14, 32)

  let y = 44

  function ensureRoom(minSpace) {
    if (y + minSpace > PAGE_BOTTOM_MARGIN) {
      doc.addPage()
      y = 20
    }
  }

  doc.setFontSize(11)
  doc.text('Section', 14, y)
  doc.text('Period', 100, y)
  doc.text('Grade', 140, y)
  doc.text('Letter', 170, y)
  y += 4
  doc.line(14, y, 196, y)
  y += 8

  reportCard.sections.forEach((section) => {
    ensureRoom(8)
    doc.setFontSize(10)
    doc.text(section.class_name, 14, y)
    doc.text(String(section.period), 100, y)
    doc.text(section.percentage != null ? formatPercent(section.percentage) : '—', 140, y)
    doc.text(section.letter_grade || '—', 170, y)
    y += 8
  })

  y += 6

  reportCard.sections.forEach((section) => {
    ensureRoom(24)

    doc.setFontSize(13)
    doc.text(section.class_name, 14, y)
    const grade = section.percentage != null ? formatPercent(section.percentage) : '—'
    const letter = section.letter_grade || '—'
    doc.text(`${grade} (${letter})`, 196, y, { align: 'right' })
    y += 6

    doc.setFontSize(10)
    doc.setTextColor(120)
    doc.text(section.teacher_name || 'Unassigned', 14, y)
    doc.setTextColor(0)
    y += 6

    doc.setFontSize(9)
    doc.text('Name', 14, y)
    doc.text('Type', 90, y)
    doc.text('Category', 118, y)
    doc.text('Assigned', 150, y)
    doc.text('Grade', 180, y)
    y += 3
    doc.line(14, y, 196, y)
    y += 6

    if (section.items.length === 0) {
      doc.setFontSize(9)
      doc.text('No assignments or quests yet.', 14, y)
      y += 8
    } else {
      section.items.forEach((item) => {
        ensureRoom(8)
        doc.setFontSize(9)
        doc.text(item.name, 14, y, { maxWidth: 72 })
        doc.text(KIND_LABELS[item.kind] || item.kind, 90, y)
        doc.text(item.category, 118, y)
        doc.text(new Date(item.assigned_at).toLocaleDateString(), 150, y)
        doc.text(item.grade != null ? formatPercent(item.grade) : '—', 180, y)
        y += 7
      })
    }

    y += 6
  })

  return doc
}

export function downloadReportCard(student, reportCard) {
  buildReportCardPdf({ student, reportCard }).save(`${student.username}-report-card.pdf`)
}

export function printReportCard(student, reportCard) {
  const doc = buildReportCardPdf({ student, reportCard })
  doc.autoPrint()
  window.open(doc.output('bloburl'), '_blank')
}
