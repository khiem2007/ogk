import type { WebCategory } from '../types/ogk';

export interface DomainCatalogEntry {
  domain: string;
  category: WebCategory;
  defaultDecision6To11: 'allow' | 'restrict' | 'block';
  sourceNote: string;
  protected?: boolean;
}

export const WEB_CATEGORY_META: Record<
  WebCategory,
  { label: string; description: string; default6To11: 'allow' | 'restrict' | 'block' }
> = {
  education: {
    label: 'Giáo dục & học liệu',
    description: 'Cổng trường học, từ điển, thư viện số và nền tảng học trực tuyến.',
    default6To11: 'allow',
  },
  entertainment: {
    label: 'Giải trí phù hợp lứa tuổi',
    description: 'Video thiếu nhi, truyện tranh giáo dục, nội dung giải trí lành mạnh.',
    default6To11: 'restrict',
  },
  social: {
    label: 'Mạng xã hội',
    description: 'Mạng xã hội và cộng đồng trò chuyện; mặc định hạn chế/chặn với nhóm 6–11 tuổi.',
    default6To11: 'block',
  },
  games: {
    label: 'Trò chơi trực tuyến',
    description: 'Cổng game trình duyệt và nền tảng chơi game trực tuyến.',
    default6To11: 'restrict',
  },
  inappropriate: {
    label: 'Không phù hợp lứa tuổi (mô phỏng)',
    description:
      'Chỉ chứa tên miền .example.test / .test trung tính để kiểm thử; tuyệt đối không dùng miền người lớn thật.',
    default6To11: 'block',
  },
  uncategorized: {
    label: 'Chưa phân loại',
    description: 'Tên miền mới hoặc chưa xác định danh mục; áp dụng quy tắc mặc định theo mode.',
    default6To11: 'restrict',
  },
};

/**
 * NT6: Protected allowlist that parents cannot disable or override in UI.
 * School portals, National Child Protection Hotline 111, emergency & rescue info.
 */
export const PROTECTED_ALLOWLIST_ENTRIES: readonly DomainCatalogEntry[] = [
  {
    domain: 'tongdai111.vn',
    category: 'education',
    defaultDecision6To11: 'allow',
    sourceNote: 'NT6 — Tổng đài quốc gia bảo vệ trẻ em 111',
    protected: true,
  },
  {
    domain: 'molisa.gov.vn',
    category: 'education',
    defaultDecision6To11: 'allow',
    sourceNote: 'NT6 — Cổng bảo vệ trẻ em & hỗ trợ khẩn cấp',
    protected: true,
  },
  {
    domain: 'moet.gov.vn',
    category: 'education',
    defaultDecision6To11: 'allow',
    sourceNote: 'NT6 — Cổng Bộ Giáo dục và Đào tạo',
    protected: true,
  },
  {
    domain: 'hcm.edu.vn',
    category: 'education',
    defaultDecision6To11: 'allow',
    sourceNote: 'NT6 — Cổng thông tin trường học',
    protected: true,
  },
  {
    domain: 'vnedu.vn',
    category: 'education',
    defaultDecision6To11: 'allow',
    sourceNote: 'NT6 — Cổng học bạ và kết nối nhà trường',
    protected: true,
  },
  {
    domain: 'chinhphu.vn',
    category: 'education',
    defaultDecision6To11: 'allow',
    sourceNote: 'NT6 — Cổng thông tin cứu hộ & công dân',
    protected: true,
  },
];

const EDUCATION_BASE = [
  'khanacademy.org',
  'vi.khanacademy.org',
  'wikipedia.org',
  'vi.wikipedia.org',
  'wiktionary.org',
  'oxfordlearnersdictionaries.com',
  'dictionary.cambridge.org',
  'tratu.soha.vn',
  'olm.vn',
  'vio.edu.vn',
  'hocmai.vn',
  'tuyensinh247.com',
  'coursera.org',
  'edx.org',
  'scratch.mit.edu',
  'code.org',
  'duolingo.com',
  'typingclub.com',
  'geogebra.org',
  'desmos.com',
  'phet.colorado.edu',
  'nasa.gov',
  'spaceplace.nasa.gov',
  'nationalgeographic.com',
  'kids.nationalgeographic.com',
  'britannica.com',
  'kids.britannica.com',
  'ted.com',
  'ed.ted.com',
  'library.example.test',
  'school-portal.example.test',
  'math-lab.example.test',
  'science-club.example.test',
  'vietnam-history.example.test',
  'english-reading.example.test',
  'informatics-olympiad.example.test',
  'physics-sim.example.test',
  'chemistry-safe.example.test',
  'geography-atlas.example.test',
];

const ENTERTAINMENT_BASE = [
  'youtubekids.com',
  'vtv7.vtv.vn',
  'thieunien.vn',
  'muctim.tuoitre.vn',
  'nhidong.vn',
  'storylineonline.net',
  'pbskids.org',
  'funbrain.com',
  'highlights.com',
  'crayola.com',
  'nickjr.com',
  'sesamestreet.org',
  'disneynow.com',
  'kids-music.example.test',
  'science-cartoon.example.test',
  'origami-club.example.test',
  'bedtime-story.example.test',
  'nature-doc.example.test',
  'kids-podcast.example.test',
  'drawing-studio.example.test',
  'chess-club.example.test',
  'magic-science.example.test',
  'animal-planet-kids.example.test',
  'museum-tour.example.test',
  'music-theory.example.test',
  'kids-radio.example.test',
  'robotics-show.example.test',
  'astronomy-kids.example.test',
  'craft-ideas.example.test',
  'story-audio.example.test',
  'kids-cinema.example.test',
  'folktales.example.test',
  'reading-corner.example.test',
  'piano-practice.example.test',
];

const SOCIAL_BASE = [
  'facebook.com',
  'instagram.com',
  'tiktok.com',
  'threads.net',
  'x.com',
  'twitter.com',
  'snapchat.com',
  'discord.com',
  'reddit.com',
  'pinterest.com',
  'tumblr.com',
  'zalo.me',
  'telegram.org',
  'messenger.com',
  'whatsapp.com',
  'line.me',
  'viber.com',
  'wechat.com',
  'weibo.com',
  'linkedin.com',
  'twitch.tv',
  'social-feed.example.test',
  'chat-room.example.test',
  'short-video.example.test',
  'forum-community.example.test',
  'livestream-chat.example.test',
  'microblog.example.test',
  'photo-share.example.test',
  'voice-hangout.example.test',
  'fan-club.example.test',
  'group-board.example.test',
  'story-reel.example.test',
  'teen-network.example.test',
  'public-wall.example.test',
];

const GAMES_BASE = [
  'roblox.com',
  'minecraft.net',
  'poki.com',
  'crazygames.com',
  'coolmathgames.com',
  'chess.com',
  'lichess.org',
  'store.steampowered.com',
  'epicgames.com',
  'ea.com',
  'ubisoft.com',
  'nintendo.com',
  'playvalorant.com',
  'leagueoflegends.com',
  'fortnite.com',
  'brawlstars.com',
  'friv.com',
  'y8.com',
  'kongregate.com',
  'miniclip.com',
  'armor-games.example.test',
  'puzzle-arena.example.test',
  'racing-arcade.example.test',
  'block-builder.example.test',
  'tower-defense.example.test',
  'pixel-quest.example.test',
  'card-duel.example.test',
  'space-shooter.example.test',
  'word-quest.example.test',
  'boardgame-hub.example.test',
  'sports-mini.example.test',
  'strategy-zone.example.test',
  'retro-arcade.example.test',
  'sandbox-world.example.test',
];

const INAPPROPRIATE_SIMULATION_BASE = Array.from(
  { length: 34 },
  (_, index) => `restricted-sim-${String(index + 1).padStart(2, '0')}.example.test`,
);

const UNCATEGORIZED_BASE = Array.from(
  { length: 34 },
  (_, index) => `unknown-site-${String(index + 1).padStart(2, '0')}.test`,
);

/**
 * Full safe categorization dataset with 6 official PDF categories and >= 200 entries.
 * Provenance:
 * - Protected allowlist per NT6
 * - Public educational / safe portals per PDF Appendix p.12
 * - Safe .example.test / .test placeholders for prohibited/unknown simulations (never real adult sites)
 */
export const DOMAIN_CATALOG: readonly DomainCatalogEntry[] = [
  ...PROTECTED_ALLOWLIST_ENTRIES,
  ...EDUCATION_BASE.map((domain) => ({
    domain,
    category: 'education' as const,
    defaultDecision6To11: 'allow' as const,
    sourceNote: 'Bộ giáo dục & cổng học tập an toàn',
  })),
  ...ENTERTAINMENT_BASE.map((domain) => ({
    domain,
    category: 'entertainment' as const,
    defaultDecision6To11: 'restrict' as const,
    sourceNote: 'Giải trí phù hợp lứa tuổi 6–11',
  })),
  ...SOCIAL_BASE.map((domain) => ({
    domain,
    category: 'social' as const,
    defaultDecision6To11: 'block' as const,
    sourceNote: 'Mạng xã hội & nhắn tin cộng đồng',
  })),
  ...GAMES_BASE.map((domain) => ({
    domain,
    category: 'games' as const,
    defaultDecision6To11: 'restrict' as const,
    sourceNote: 'Trò chơi trực tuyến theo ngân sách thời gian',
  })),
  ...INAPPROPRIATE_SIMULATION_BASE.map((domain) => ({
    domain,
    category: 'inappropriate' as const,
    defaultDecision6To11: 'block' as const,
    sourceNote: 'Miền mô phỏng trung tính theo quy định đề bài PDF trang 7 & 12',
  })),
  ...UNCATEGORIZED_BASE.map((domain) => ({
    domain,
    category: 'uncategorized' as const,
    defaultDecision6To11: 'restrict' as const,
    sourceNote: 'Miền mới chưa phân loại phục vụ kiểm thử rule mặc định',
  })),
];
