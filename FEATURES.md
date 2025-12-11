# Alliance Dashboard - Feature Guide

## 🎯 Current Features

### **Core Functionality**
- ✅ Real-time announcement scraping from multiple schools
- ✅ Automatic PDF text extraction
- ✅ MongoDB storage with JSON fallback
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Anti-CAPTCHA measures with configurable delays

### **Dashboard Views**
- ✅ **Table View** - Traditional sortable table
- ✅ **Card View** - Modern card layout with hover effects
- ✅ **Toggle between views** - Switch with one click

### **Statistics Cards**
- 📊 **Total Announcements** - Click to show all
- ⭐ **Highlighted** - Click to filter important items
- ✅ **Open** - Click to show active opportunities
- 🕒 **Recent** - Latest announcements

### **Filtering & Search**
- 🔍 **Instant Search** - Real-time filtering (Ctrl/Cmd+K)
- 🏫 **School Filter** - Filter by specific school
- 🎯 **Quick Filters** - All, Highlighted, Open
- 📅 **Date Sorting** - Sort by publication date
- 🏷️ **Category/City Filter** - Filter by metadata

### **Bulk Operations**
- ☑ **Select All** - Select all visible announcements (Ctrl/Cmd+A)
- 👁 **Bulk Mark as Read** - Mark multiple as read
- ⊘ **Bulk Skip** - Mark multiple as non-relevant
- 📥 **Export CSV** - Export filtered results (Ctrl/Cmd+E)

### **Personal State Tracking**
- 📝 **Mark as Read** - Track viewed announcements
- 📤 **Applied** - Mark when you've submitted application
- ❌ **Skip** - Mark as not relevant
- 💾 **LocalStorage** - Saves your progress locally

### **Detail Pages**
- 📄 **Full Content** - Complete announcement details
- 📎 **Attachments** - View and download files
- 📑 **PDF Viewer** - Inline PDF viewing + text extraction
- ⬅️➡️ **Navigation** - Previous/Next announcement buttons
- 📱 **Share** - Direct link to announcement

### **Keyboard Shortcuts**

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Focus search box |
| `Escape` | Clear search |
| `Ctrl/Cmd + A` | Select all visible |
| `Ctrl/Cmd + E` | Export to CSV |
| `Enter` | Open selected announcement |

### **Data Export**
- **CSV Export** - Export filtered results with:
  - ID, Title, School, City, Category, Date, Status, Link
  - Automatic filename with date
  - Proper CSV escaping

### **Accessibility**
- ♿ **ARIA Labels** - Screen reader support
- ⌨️ **Keyboard Navigation** - Full keyboard support
- 🎨 **High Contrast** - Dark theme with good contrast
- 📱 **Responsive** - Works on all devices

## 🚀 How to Use

### **Quick Start**
1. Open http://localhost:5000
2. Browse announcements in table or card view
3. Click stat cards to quickly filter
4. Use search box (Ctrl+K) to find specific items
5. Mark items as read/applied/skip to track progress

### **Power User Features**

#### **Bulk Operations**
1. Check boxes next to announcements (or Ctrl+A for all)
2. Use quick action buttons to mark multiple items
3. Selection count shows in real-time

#### **Export Workflow**
1. Apply your filters (search, school, status)
2. Click "📥 Esporta CSV" or press Ctrl+E
3. CSV downloads with current date in filename
4. Open in Excel/Google Sheets

#### **Efficient Navigation**
1. Use clickable stat cards for instant filtering
2. Keyboard shortcuts for speed
3. Personal state tracking to avoid duplicates
4. Previous/Next navigation in detail view

## 📊 Statistics Dashboard

### **What the Cards Show:**
- **Total Annunci**: All announcements in database
- **Evidenziati**: Important/highlighted opportunities
- **Aperti**: Currently open positions/calls
- **Recenti**: Announcements from last 7 days

### **Interactive Filtering:**
- Click any stat card to filter by that category
- Active card has blue border highlight
- Chip filters update automatically
- All filters work together (search + school + status)

## 💡 Tips & Tricks

### **Finding Relevant Opportunities**
1. Click "Aperti" stat card to see only open calls
2. Use school filter to focus on your area
3. Search for keywords like "bando", "tutor", "selezione"
4. Sort by date to see latest first

### **Managing Your Applications**
1. Mark announcements as "Read" after viewing
2. Change to "Candidatura inviata" after applying
3. Use "Non rilevante" to hide irrelevant items
4. Export filtered list for tracking

### **Bulk Processing**
1. Use "Solo evidenziati" chip filter
2. Select all with checkbox in header
3. Bulk mark as "Read"
4. Export remaining to CSV

### **Keyboard Power User**
```
Ctrl+K → Search
Type keywords
Enter → Open first result
Alt+← → Back to list
Ctrl+E → Export filtered
```

## 🔄 Workflow Examples

### **Weekly Review**
1. Click "Recenti" stat card
2. Review all new announcements
3. Mark relevant ones as "Read"
4. Skip irrelevant ones

### **Application Campaign**
1. Filter by school or category
2. Select all relevant announcements
3. Mark as "Read" to review later
4. Export CSV for spreadsheet tracking

### **Monitoring Specific Schools**
1. Use school filter dropdown
2. Click "Aperti" for active opportunities
3. Set up weekly fetch schedule
4. Check dashboard for updates

## 🎨 UI Customization

### **Available Views**
- **Table View**: Dense, sortable, professional
- **Card View**: Visual, spacious, modern
- Switch anytime with view toggle buttons

### **Responsive Breakpoints**
- **Desktop** (>900px): Full 4-column stats, wide table
- **Tablet** (600-900px): 2-column stats, scrollable table
- **Mobile** (<600px): 1-column stats, card view recommended

## 🔒 Privacy & Data

### **What's Stored Locally:**
- Personal states (read/applied/skip) in browser localStorage
- No personal data sent to server
- Clear browser data to reset states

### **What's Stored in Database:**
- Scraped announcements
- School information
- No user tracking or analytics

## 📈 Future Enhancements (Roadmap)

### **Planned Features:**
- 📅 Date range picker
- 💾 Saved filter presets
- 🔔 Browser notifications for new announcements
- 📧 Email digest subscriptions
- 🗓️ Calendar integration (export deadlines)
- 📝 Personal notes on announcements
- 🔗 Share filtered views via URL
- 🌙 Light mode theme option
- 📱 Progressive Web App (PWA)
- 🤖 AI-powered relevance scoring

### **Technical Improvements:**
- Advanced search operators (AND, OR, NOT)
- Full-text search in PDF content
- Deadline tracking and alerts
- Application deadline countdown
- Duplicate detection
- Auto-categorization using ML

## 🐛 Known Limitations

1. **CAPTCHA Challenges**: Some schools may trigger CAPTCHAs
   - Solution: Configure delays in `.env`
   - Use headful mode for manual solving

2. **PDF Extraction**: Not all PDFs extract text perfectly
   - Scanned images won't have searchable text
   - Use iframe viewer for visual inspection

3. **Update Frequency**: Manual or scheduled fetching only
   - No real-time updates
   - Run fetch command when needed

4. **Browser Compatibility**: Best in modern browsers
   - Chrome, Firefox, Edge, Safari (latest versions)
   - IE11 not supported

## 📞 Support

### **Common Issues:**

**Q: Stats not updating after fetch?**
A: Refresh the page (F5)

**Q: Personal states disappeared?**
A: Check if localStorage was cleared or if you're in incognito mode

**Q: Export not working?**
A: Check browser's download settings and popup blocker

**Q: Keyboard shortcuts not working?**
A: Check if another extension is capturing the shortcuts

**Q: CAPTCHAs appearing frequently?**
A: Increase delays in `.env` file (see DEPLOYMENT.md)

## 📚 Documentation

- `README.md` - Setup and installation
- `DEPLOYMENT.md` - Production deployment & CAPTCHA handling
- `FEATURES.md` - This file (feature guide)
- `USAGE.txt` - Quick reference card

## 🎉 Credits

Built with:
- Flask (Python backend)
- TypeScript (Frontend logic)
- Beautiful Soup (Web scraping)
- PyPDF2 (PDF extraction)
- Playwright (CAPTCHA handling)
- MongoDB (Data storage)
