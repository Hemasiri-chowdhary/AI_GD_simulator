"""GD Topic Service - Loads and manages discussion topics."""
import json
import random
import logging
from pathlib import Path
from collections import Counter, defaultdict, deque
from typing import List, Dict, Optional, Deque

from app.models.schemas import TopicInfo, CategoryInfo

logger = logging.getLogger(__name__)


# Default topics if file not found
DEFAULT_TOPICS = {
    "Current Affairs": [
        {
            "id": "ca1",
            "title": "Impact of AI on Employment",
            "description": "Should we be concerned about AI replacing human jobs in the next decade?",
            "difficulty": "medium"
        },
        {
            "id": "ca2",
            "title": "Climate Change Policies",
            "description": "Are current global climate change policies sufficient?",
            "difficulty": "medium"
        },
        {
            "id": "ca3",
            "title": "Digital Privacy vs National Security",
            "description": "How should governments balance surveillance with citizen privacy?",
            "difficulty": "hard"
        },
        {
            "id": "ca4",
            "title": "Remote Work Culture",
            "description": "Is remote work the future or should companies return to office?",
            "difficulty": "easy"
        }
    ],
    "Technology": [
        {
            "id": "tech1",
            "title": "Social Media's Impact on Society",
            "description": "Has social media done more harm than good to society?",
            "difficulty": "medium"
        },
        {
            "id": "tech2",
            "title": "Cryptocurrency as Future Currency",
            "description": "Will cryptocurrency replace traditional banking systems?",
            "difficulty": "hard"
        },
        {
            "id": "tech3",
            "title": "5G and Health Concerns",
            "description": "Are concerns about 5G technology justified?",
            "difficulty": "medium"
        },
        {
            "id": "tech4",
            "title": "Open Source vs Proprietary Software",
            "description": "Which model is better for technological innovation?",
            "difficulty": "medium"
        }
    ],
    "Abstract Topics": [
        {
            "id": "abs1",
            "title": "The Color of Success",
            "description": "What does success look like and who defines it?",
            "difficulty": "hard"
        },
        {
            "id": "abs2",
            "title": "Silence Speaks Louder Than Words",
            "description": "When is silence more powerful than speaking up?",
            "difficulty": "hard"
        },
        {
            "id": "abs3",
            "title": "The Journey vs The Destination",
            "description": "Which matters more in life - the journey or reaching the destination?",
            "difficulty": "medium"
        },
        {
            "id": "abs4",
            "title": "Time is Money",
            "description": "Is this statement true in today's world?",
            "difficulty": "easy"
        }
    ],
    "Business & Economy": [
        {
            "id": "biz1",
            "title": "Startups vs Corporate Jobs",
            "description": "Is it better to work for a startup or an established corporation?",
            "difficulty": "easy"
        },
        {
            "id": "biz2",
            "title": "Globalization Benefits",
            "description": "Has globalization benefited developing countries?",
            "difficulty": "medium"
        },
        {
            "id": "biz3",
            "title": "Universal Basic Income",
            "description": "Should governments implement Universal Basic Income?",
            "difficulty": "hard"
        },
        {
            "id": "biz4",
            "title": "Ethical Consumerism",
            "description": "Can consumer choices truly drive corporate change?",
            "difficulty": "medium"
        }
    ],
    "Ethics & Society": [
        {
            "id": "eth1",
            "title": "Right to Privacy in Digital Age",
            "description": "Is complete privacy possible or even desirable in the digital age?",
            "difficulty": "medium"
        },
        {
            "id": "eth2",
            "title": "Affirmative Action Policies",
            "description": "Are reservation and affirmative action policies still relevant?",
            "difficulty": "hard"
        },
        {
            "id": "eth3",
            "title": "Capital Punishment",
            "description": "Should capital punishment be abolished worldwide?",
            "difficulty": "hard"
        },
        {
            "id": "eth4",
            "title": "Education System Reform",
            "description": "Does our education system need a complete overhaul?",
            "difficulty": "medium"
        }
    ]
}


EXPANDED_TOPIC_SEEDS = {
    "Environment": [
        "Should cities make public transport free to reduce emissions?",
        "Is carbon tax practical for developing economies?",
        "Can individual lifestyle changes meaningfully slow climate change?",
        "Should single-use plastic be completely banned?",
        "Are electric vehicles truly sustainable end-to-end?",
        "Should climate education be mandatory in schools?",
        "Can green jobs offset losses in fossil-fuel sectors?",
        "Should governments subsidize rooftop solar for all households?",
        "Is nuclear energy essential for a clean-energy transition?",
        "Can eco-tourism protect biodiversity better than strict restrictions?",
        "Should companies publish verified annual carbon disclosures?",
        "Are urban heat islands now a public-health emergency?",
    ],
    "Education": [
        "Should schools prioritize skills over marks?",
        "Is hybrid learning superior to traditional classrooms?",
        "Should internships be compulsory in all degree programs?",
        "Do standardized tests fairly measure student ability?",
        "Should AI tutors be integrated into regular teaching?",
        "Is coding literacy now as important as language literacy?",
        "Should universities include mandatory communication training?",
        "Are gap years beneficial for career readiness?",
        "Should vocational tracks be promoted equally with degrees?",
        "Can project-based assessment replace written exams?",
        "Should teachers be evaluated partly through student outcomes?",
        "Is entrepreneurship education needed from school level?",
    ],
    "AI Ethics": [
        "Should AI-generated content always carry disclosure labels?",
        "Who is accountable when an AI system causes harm?",
        "Should facial recognition be limited in public spaces?",
        "Can AI bias ever be fully eliminated?",
        "Should AI models trained on public data require consent layers?",
        "Is autonomous weapons development ethically defensible?",
        "Should deepfakes be criminalized beyond satire and art?",
        "Do companies need external audits for high-risk AI systems?",
        "Should students rely on AI tools for assignments?",
        "Can AI governance keep pace with rapid innovation?",
        "Should AI companions for children face strict regulation?",
        "Is open-source AI safer than closed proprietary AI?",
    ],
    "Startups": [
        "Should founders prioritize profitability over growth early on?",
        "Is bootstrapping better than early venture funding?",
        "Do startup accelerators meaningfully improve success odds?",
        "Should startups adopt remote-first teams by default?",
        "Is founder-led sales critical in the first two years?",
        "Should startup failure be normalized in hiring decisions?",
        "Can product-led growth replace traditional marketing in B2B?",
        "Should startups focus domestic markets before global expansion?",
        "Is equity compensation enough to attract top talent?",
        "Do startup pivots signal strength or weak strategy?",
        "Should government procurement favor early-stage startups?",
        "Can sustainability be a core moat for startups?",
    ],
    "Global Issues": [
        "Should developed nations fund climate adaptation in poorer countries?",
        "Is global trade becoming too geopolitically fragmented?",
        "Should digital public infrastructure be treated as a global public good?",
        "Can international law effectively govern cyber warfare?",
        "Should migration policy prioritize skills-based models?",
        "Is food security the biggest global risk this decade?",
        "Should countries cap strategic dependence on single suppliers?",
        "Can global institutions still solve cross-border crises effectively?",
        "Should vaccine technologies be shared during global emergencies?",
        "Is water scarcity the next major source of geopolitical conflict?",
        "Should social media platforms be globally regulated?",
        "Can ethical supply chains stay competitive in price-sensitive markets?",
    ]
}

CATEGORY_ICONS = {
    "Current Affairs": "📰",
    "Technology": "💻",
    "Abstract Topics": "🎨",
    "Business & Economy": "💼",
    "Ethics & Society": "⚖️",
    "Environment": "🌱",
    "Education": "📚",
    "AI Ethics": "🤖",
    "Startups": "🚀",
    "Global Issues": "🌍"
}


class TopicService:
    """Service for managing GD topics."""
    
    def __init__(self, topics_file: Optional[str] = None):
        self.topics = self._load_topics(topics_file)
        self._expand_topics_for_diversity(min_topics_per_category=110)
        self.category_usage_counter: Counter = Counter()
        self.topic_usage_counter: Counter = Counter()
        self.user_recent_topics: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=10))
        self.global_recent_topics: Deque[str] = deque(maxlen=10)
        
    def _load_topics(self, topics_file: Optional[str]) -> Dict[str, List[Dict]]:
        """Load topics from file or use defaults."""
        if topics_file:
            try:
                path = Path(topics_file)
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as e:
                logger.error(f"Error loading topics file: {e}")
        
        merged = dict(DEFAULT_TOPICS)
        for category, prompts in EXPANDED_TOPIC_SEEDS.items():
            seed_topics = merged.get(category, [])
            for idx, prompt in enumerate(prompts, start=1):
                seed_topics.append({
                    "id": f"{category.lower().replace(' ', '_')}_seed_{idx}",
                    "title": prompt,
                    "description": f"Discuss with practical examples and balanced viewpoints: {prompt}",
                    "difficulty": random.choice(["easy", "medium", "hard"])
                })
            merged[category] = seed_topics
        return merged

    def _expand_topics_for_diversity(self, min_topics_per_category: int = 110) -> None:
        """Expand each category to a large topic bank with contextual variants."""
        angle_templates = [
            "from the perspective of employability",
            "in the context of India and other developing economies",
            "considering long-term societal impact",
            "with a focus on policy and regulation",
            "through the lens of ethics and fairness",
            "for college students entering the job market",
            "for public sector versus private sector priorities",
            "with short-term vs long-term trade-offs",
            "from urban versus rural implementation realities",
            "considering affordability and accessibility",
            "from innovation versus risk-management priorities",
            "for both consumers and institutions"
        ]

        for category, topics in list(self.topics.items()):
            if not topics:
                continue

            next_index = len(topics) + 1
            base_snapshot = list(topics)

            while len(topics) < min_topics_per_category:
                seed = base_snapshot[(next_index - 1) % len(base_snapshot)]
                angle = angle_templates[(next_index - 1) % len(angle_templates)]
                title = f"{seed.get('title', 'GD Topic')} ({angle})"
                topics.append({
                    "id": f"{category.lower().replace(' ', '_')}_{next_index}",
                    "title": title,
                    "description": f"{seed.get('description', 'Discuss in a structured GD format.')} Also evaluate this angle: {angle}.",
                    "difficulty": seed.get("difficulty", "medium")
                })
                next_index += 1

            self.topics[category] = topics

    def _get_category_key(self, category: str) -> Optional[str]:
        """Resolve a category key with case-insensitive matching."""
        if category in self.topics:
            return category

        category_lower = category.lower()
        for cat_name in self.topics:
            if cat_name.lower() == category_lower:
                return cat_name
        return None

    def _select_balanced_category(self) -> Optional[str]:
        """Pick a category with weighted balancing toward underused categories."""
        if not self.topics:
            return None

        categories = list(self.topics.keys())
        usages = [self.category_usage_counter.get(cat, 0) for cat in categories]
        max_usage = max(usages) if usages else 0
        weights = [(max_usage - usage + 1) for usage in usages]
        return random.choices(categories, weights=weights, k=1)[0]

    def _available_topics_with_memory_filter(self, category: str, user_key: str) -> List[TopicInfo]:
        """Return topics excluding globally/user-recent items where possible."""
        topics = self.get_topics_by_category(category)
        if not topics:
            return []

        blocked = set(self.global_recent_topics) | set(self.user_recent_topics[user_key])
        filtered = [topic for topic in topics if topic.id not in blocked]
        return filtered or topics

    def _weighted_topic_choice(self, topics: List[TopicInfo]) -> TopicInfo:
        """Choose topic with weights favoring less-used topics."""
        if len(topics) == 1:
            return topics[0]

        usage_counts = [self.topic_usage_counter.get(topic.id, 0) for topic in topics]
        max_usage = max(usage_counts) if usage_counts else 0
        weights = [(max_usage - count + 1) for count in usage_counts]
        return random.choices(topics, weights=weights, k=1)[0]

    def _record_topic_usage(self, topic: TopicInfo, category: str, user_key: str) -> None:
        """Store topic usage for anti-repeat memory and balancing."""
        self.topic_usage_counter[topic.id] += 1
        self.category_usage_counter[category] += 1
        self.global_recent_topics.append(topic.id)
        self.user_recent_topics[user_key].append(topic.id)
    
    def get_categories(self) -> List[CategoryInfo]:
        """Get all available categories."""
        categories = []
        for name, topics in self.topics.items():
            categories.append(CategoryInfo(
                id=name.lower().replace(" ", "_").replace("&", "and"),
                name=name,
                icon=CATEGORY_ICONS.get(name, "📋"),
                topics_count=len(topics)
            ))
        return categories
    
    def get_topics_by_category(self, category: str) -> List[TopicInfo]:
        """Get all topics for a category."""
        resolved_category = self._get_category_key(category)
        topics = self.topics.get(resolved_category) if resolved_category else None
        
        if not topics:
            return []
        
        return [TopicInfo(**topic) for topic in topics]
    
    def get_random_topic(self, category: str, user_key: str = "global") -> Optional[TopicInfo]:
        """Get a balanced random topic with anti-repeat memory per user/session."""
        resolved_category = self._get_category_key(category)
        if not resolved_category or category.lower() in {"any", "random", "all"}:
            resolved_category = self._select_balanced_category()

        if not resolved_category:
            return None

        candidates = self._available_topics_with_memory_filter(resolved_category, user_key)
        if not candidates:
            return None

        selected = self._weighted_topic_choice(candidates)
        self._record_topic_usage(selected, resolved_category, user_key)
        return selected
    
    def get_topic_by_id(self, topic_id: str) -> Optional[TopicInfo]:
        """Get a specific topic by ID."""
        for topics in self.topics.values():
            for topic in topics:
                if topic.get("id") == topic_id:
                    return TopicInfo(**topic)
        return None

    def record_manual_topic_usage(self, category: str, topic_title: str, user_key: str = "global") -> None:
        """Track manually selected topics to keep anti-repeat memory coherent."""
        resolved_category = self._get_category_key(category)
        if not resolved_category:
            return

        topics = self.get_topics_by_category(resolved_category)
        matched = next((t for t in topics if t.title.strip().lower() == topic_title.strip().lower()), None)
        if matched:
            self._record_topic_usage(matched, resolved_category, user_key)
