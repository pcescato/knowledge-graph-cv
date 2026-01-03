# 🕸️ AI Knowledge Graph CV Builder

[![Live Demo](https://img.shields.io/badge/Demo-Live-brightgreen)](https://knowledge-graph-cv-837592265234.europe-west1.run.app)
[![Dev.to Article](https://img.shields.io/badge/Article-Dev.to-black)](https://dev.to)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Transform your resume into an interactive knowledge graph powered by Gemini AI.**

Professional journeys aren't timelines—they're networks of interconnected skills, projects, and expertise. This tool uses AI to extract and visualize those connections.

🔗 **[Try it live](https://knowledge-graph-cv-837592265234.europe-west1.run.app)** | 📝 **[Read the story on Dev.to](#)**

---

## 🎯 Why This Project?

Traditional CVs are **chronological and linear**. They work well for continuous trajectories but fail to represent:

- Non-linear career paths
- Cross-domain expertise
- Technology interconnections
- Skill-project relationships

This project reimagines professional identity as a **knowledge graph**: nodes (skills, projects, concepts) connected by semantic relationships.

---

## ✨ Features

### 🕸️ Network Graph

Interactive force-directed graph with:

- **Click-to-focus**: Highlight direct connections
- **Color-coded nodes**: Skills (blue), Projects (green), Concepts (gray)
- **Dynamic filtering**: Filter by category
- **Adjustable spacing**: 6 levels from Compact to Mega Wide

### 🌊 Flow Diagram

Sankey visualization showing:

- **Skills → Projects → Expertise** flow
- **Weighted connections**: Band thickness = importance
- **Visual narrative**: Tell your career story

### 📊 Skills Matrix

Heatmap displaying:

- **Project × Skill relationships**
- **Quick scanning**: See which projects use which technologies
- **Insights**: Most-used skill, average skills per project

### 🤖 AI-Powered Extraction

- **Gemini Flash Preview 3.0**: Multimodal PDF analysis
- **Dense graphs**: 60-80+ relationships extracted
- **Semantic understanding**: Not just keywords—contextual connections
- **~8 seconds**: From PDF upload to interactive graph

### 🎨 User Experience

- **Demo pre-loaded**: My CV ready to explore (zero friction)
- **Multi-view dashboard**: 3 perspectives on the same data
- **Responsive controls**: Collapsible sidebar, adjustable spacing
- **English interface**: Global audience

---

## 🚀 Quick Start

### Try the Live Demo

**No installation needed!** The app loads with a demo CV:

1. 🌐 **[Open the app](https://knowledge-graph-cv-837592265234.europe-west1.run.app)**
2. 🔍 Explore the 3 views (sidebar: Network / Flow / Matrix)
3. 📤 Upload your own PDF CV to try it

---

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- Google API Key ([Get one here](https://aistudio.google.com/apikey))

### Local Setup

```bash
# Clone the repository
git clone https://github.com/pcescato/knowledge-graph-cv.git
cd knowledge-graph-cv

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "GOOGLE_API_KEY=your_api_key_here" > .env

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 📦 Deployment

### Google Cloud Run (Recommended)

```bash
# Build Docker image
docker build -t knowledge-graph-cv .

# Tag for Google Container Registry
docker tag knowledge-graph-cv gcr.io/YOUR_PROJECT/knowledge-graph-cv

# Push to GCR
docker push gcr.io/YOUR_PROJECT/knowledge-graph-cv

# Deploy to Cloud Run
gcloud run deploy knowledge-graph-cv \
  --image gcr.io/YOUR_PROJECT/knowledge-graph-cv \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=your_key
```

### Alternative: Streamlit Cloud

1. Fork this repository
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Add `GOOGLE_API_KEY` to secrets
4. Deploy!

---

## 🧰 Tech Stack

### AI & Data Processing

- **Gemini Flash Preview 3.0** (via Google AI API): PDF analysis & graph extraction
- **Google AI Studio**: Prompt engineering & testing

### Visualization

- **Streamlit**: Web framework & UI
- **streamlit-agraph**: Network graph (vis.js wrapper)
- **Plotly**: Sankey diagrams & heatmaps
- **NetworkX**: Graph algorithms & validation

### Deployment

- **Google Cloud Run**: Serverless container deployment
- **Docker**: Containerization

---

## 📐 Architecture

```
PDF Upload → Gemini API → JSON Graph → Multi-View Dashboard
                                        ├─ Network Graph (vis.js)
                                        ├─ Flow Diagram (Plotly Sankey)
                                        └─ Skills Matrix (Plotly Heatmap)
```

### Graph Structure

```json
{
  "nodes": [
    {"id": "python", "label": "Python", "type": "Skill", "importance": 10}
  ],
  "edges": [
    {"from": "python", "to": "ai_automation", "label": "ENABLES"}
  ]
}
```

**Relationship types**:

- `MASTERS`, `USES`, `CREATES`: Direct actions
- `ENABLES`, `REQUIRES`, `BUILT_WITH`: Technical dependencies
- `DEMONSTRATES`, `IMPLEMENTED_IN`: Conceptual connections
- `EXPERTISE_IN`, `RELATED_TO`: Meta relationships

---

## 🎨 Design Decisions

### Why streamlit-agraph for Network Visualization?

I evaluated several libraries for the interactive Network Graph:

| Library                | Interactivity | Responsive      | Dev Time |
| ---------------------- | ------------- | --------------- | -------- |
| **streamlit-agraph** ✅ | Excellent     | Fixed (1400px)  | 2 hours  |
| Plotly Graph Objects   | Limited       | 100% responsive | 6 hours  |
| D3.js Custom           | Full control  | 100% responsive | 8+ hours |

**Decision**: streamlit-agraph

**Why?** In a 2-day iteration cycle with real user feedback, **interaction quality** was more valuable than perfect iframe responsiveness.

**Trade-off accepted**: Fixed 1400×900px canvas. Works great on desktop (1440px+), less optimal in narrow embeds. The collapsible sidebar provides ~250px of extra space when needed.

### Why 3 Visualizations?

**Different audiences need different views**:

- **Developers**: Want to explore connections (Network Graph)
- **Recruiters**: Need quick visual narratives (Flow Diagram)
- **Managers**: Want fast skill scanning (Skills Matrix)

One visualization can't serve all needs.

---

## 📊 Project Metrics

### Technical

- **Nodes**: 25-35 (average per CV)
- **Relationships**: 60-80 (average)
- **Density**: 2.0-2.8 edges/node
- **Extraction Time**: ~20 seconds (Gemini Flash Preview 3.0)
- **Supported Formats**: PDF only
- **Visualizations**: 3 modes

### Development

- **Versions**: V1 → V8.3 (8 major iterations)
- **Prompt iterations**: 20+ (Google AI Studio)
- **User feedback cycles**: Multiple
- **Lines of code**: ~1,200

---

## 🎓 How It Works

### 1. Prompt Engineering (Google AI Studio)

Before writing any application code, I spent time in AI Studio crafting a multi-level extraction prompt:

```
LEVEL 1: Core entities (Person, Skills, Projects)
LEVEL 2: Relationships (USES, CREATED, MASTERS)
LEVEL 3: Technical relationships (PHP ENABLES WordPress)
LEVEL 4: Concepts & expertise domains
LEVEL 5: Temporal & contextual relationships
LEVEL 6: Bidirectional concept-project links
```

The prompt evolved through 20+ iterations in AI Studio before integration.

### 2. Semantic Extraction

The system doesn't just extract keywords—it reasons about context:

**Example**: "Built a WordPress migration tool in Python"

**Extracted graph**:

- Python ENABLES Migration Engineering
- Migration Engineering IMPLEMENTED_IN Migration Tool
- Migration Tool DEMONSTRATES Migration Engineering
- Migration Tool USES Python
- Migration Tool USES WordPress

**Bidirectional semantic relationships** create graph completeness.

### 3. Multi-View Rendering

The same JSON graph is rendered in 3 ways:

- **Network**: Force-directed layout (streamlit-agraph)
- **Flow**: Sankey diagram (Plotly)
- **Matrix**: Heatmap (Plotly)

User switches views via sidebar radio button—**instant switching** (1 click, no reload).

---

## 🧪 Example Use Cases

### For Job Seekers

- **Portfolio enhancement**: Show interconnected skills
- **Interview preparation**: Visualize your expertise domains
- **Gap analysis**: Identify under-connected skills

### For Recruiters

- **Quick assessment**: 30-second skill scan (Matrix view)
- **Depth evaluation**: Explore project connections (Network view)
- **Story telling**: See candidate's journey (Flow view)

### For Career Counselors

- **Career path visualization**: Show non-linear trajectories
- **Skill planning**: Identify development opportunities
- **Portfolio building**: Help clients present themselves better

---

## 🤝 Contributing

Contributions welcome! This project was built in 2 days with iterative feedback—there's room for improvement.

**Ideas for contribution**:

- [ ] Export formats (GraphML, Neo4j cypher, JSON-LD)
- [ ] Comparison mode (two CVs side-by-side)
- [ ] Temporal dimension (career evolution over time)
- [ ] Skills gap analysis (compare against job descriptions)
- [ ] Alternative graph libraries (Plotly native, D3.js)
- [ ] Multi-language support (currently English only)

**To contribute**:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 Development Log

**V1-V3**: POC → Dense graph (30 nodes, 70+ edges)  
**V4-V6**: Spacing optimization + bidirectional relationships  
**V7.0-7.6**: Multi-view dashboard + readability iterations  
**V8.0-8.1**: English interface + demo CV auto-loading  
**V8.2**: Radio button instant switching fix  
**V8.3**: Final polish (hero message, instructions, footer) ✅

**Total**: 8 major versions based on real user feedback.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Pascal Cescato**

- 🌐 Website: [pascalcescato.com](https://pascalcescato.com)
- 💼 LinkedIn: [linkedin.com/in/pascalcescato](https://linkedin.com/in/pascalcescato)
- 📝 Dev.to: [@pcescato](https://dev.to/pcescato)
- 🐙 GitHub: [@pcescato](https://github.com/pcescato)

---

## 🙏 Acknowledgments

- **Google AI Studio**: Invaluable for prompt engineering & iteration
- **Gemini Flash Preview 3.0**: Fast, accurate multimodal analysis
- **Streamlit Community**: Excellent framework for rapid prototyping
- **vis.js**: Powerful force-directed graph visualization
- **Dev.to Challenge**: Motivation to build and ship in 2 days

---

## 📚 Related Resources

- 📝 **[Dev.to Article](#)**: Full story & technical deep-dive
- 🎓 **[Google AI Studio](https://aistudio.google.com)**: Try prompt engineering yourself
- 📖 **[Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)**: Prompt design principles
- 🕸️ **[vis.js Documentation](https://visjs.org/)**: Network visualization library

---

## 🐛 Known Limitations

### Canvas Size

- Network Graph uses fixed 1400×900px canvas (streamlit-agraph limitation)
- Works great on desktop (1440px+), less optimal in narrow iframes
- **Mitigation**: Collapsible sidebar adds ~250px when needed

### PDF Support Only

- Currently supports PDF input only
- DOCX support planned for future versions

### Single Language

- Interface in English only
- Internationalization planned

### No Persistence

- Graphs are session-only (not saved server-side)
- Export functionality planned

---

## 🎯 New Year, New You

*This project was created for the [Dev.to "New Year, New You" Challenge](https://dev.to/challenges/new-year-new-you-google-ai-2025-12-31), powered by Google AI.*

**Theme alignment**: Rather than reinventing yourself, sometimes you just need to **represent yourself differently**. This tool helps visualize professional identity as it truly is—a network of connections, not a linear timeline.

---

## ⭐ Star this project!

If you find this project useful, please consider giving it a ⭐ on GitHub. It helps others discover the project!

**Questions? Issues?** [Open an issue](https://github.com/pcescato/knowledge-graph-cv/issues) or reach out!

---

**Built with ❤️ and AI in 2 days | Deployed on Google Cloud Run**
