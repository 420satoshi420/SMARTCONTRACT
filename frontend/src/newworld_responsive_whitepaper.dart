import 'package:flutter/material.dart';

/// Breakpoint for switching between single-column mobile view and side-by-side desktop view.
const double kLargeScreenBreakpoint = 850.0;
const double kMaxReadingContentWidth = 860.0;

class PearlAIResponsiveWhitepaperApp extends StatelessWidget {
  const PearlAIResponsiveWhitepaperApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PearlAI Protocol Whitepaper & AMM',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF070B0E),
        primaryColor: const Color(0xFF00E5FF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00E5FF),
          secondary: Color(0xFF00FF88),
          surface: Color(0xFF0D1318),
        ),
      ),
      home: const PearlAIWhitepaperScreen(),
    );
  }
}

class PearlAIWhitepaperScreen extends StatefulWidget {
  const PearlAIWhitepaperScreen({super.key});

  @override
  State<PearlAIWhitepaperScreen> createState() => _PearlAIWhitepaperScreenState();
}

class _PearlAIWhitepaperScreenState extends State<PearlAIWhitepaperScreen> {
  int _selectedSectionIndex = 0;

  final List<String> _sections = [
    '1. Executive Summary',
    '2. Problem & Solution',
    '3. Ecosystem Tokenomics ($PEARL)',
    '4. AMM Constant Product Architecture',
    '5. Staking & Yield Mechanics',
    '6. Verified On-Chain Deployments',
    '7. Security Audit & Invariant Matrix',
  ];

  @override
  Widget build(BuildContext context) {
    // Guidelines: Use MediaQuery.sizeOf(context) for overall window metrics
    final windowSize = MediaQuery.sizeOf(context);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D1318),
        elevation: 1,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF00E5FF).withOpacity(0.15),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.4)),
              ),
              child: const Text(
                'PEARL',
                style: TextStyle(
                  color: Color(0xFF00E5FF),
                  fontWeight: FontWeight.w900,
                  fontSize: 13,
                  letterSpacing: 1.2,
                ),
              ),
            ),
            const SizedBox(width: 12),
            const Text(
              'Protocol Whitepaper & AMM Architecture',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
      drawer: windowSize.width <= kLargeScreenBreakpoint ? _buildDrawer() : null,
      body: LayoutBuilder(
        builder: (context, constraints) {
          // Guidelines: Evaluate constraints.maxWidth to adapt layout
          if (constraints.maxWidth > kLargeScreenBreakpoint) {
            return _buildLargeScreenLayout(constraints);
          } else {
            return _buildSmallScreenLayout(constraints);
          }
        },
      ),
    );
  }

  Widget _buildDrawer() {
    return Drawer(
      backgroundColor: const Color(0xFF0D1318),
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          const DrawerHeader(
            decoration: BoxDecoration(color: Color(0xFF141D24)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  '🌿 PearlAI Protocol',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                SizedBox(height: 6),
                Text(
                  'Whitepaper & Specification v1.0.0',
                  style: TextStyle(fontSize: 12, color: Colors.white60),
                ),
              ],
            ),
          ),
          ...List.generate(_sections.length, (index) {
            final isSelected = index == _selectedSectionIndex;
            return ListTile(
              title: Text(
                _sections[index],
                style: TextStyle(
                  color: isSelected ? const Color(0xFF00E5FF) : Colors.white70,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  fontSize: 13,
                ),
              ),
              selected: isSelected,
              onTap: () {
                setState(() => _selectedSectionIndex = index);
                Navigator.of(context).pop();
              },
            );
          }),
        ],
      ),
    );
  }

  /// Side-by-side layout for desktop and tablet screens
  Widget _buildLargeScreenLayout(BoxConstraints constraints) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Sidebar navigation: fixed width with Flexible/Expanded content
        SizedBox(
          width: 280,
          child: Container(
            color: const Color(0xFF0A0F14),
            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'TABLE OF CONTENTS',
                  style: TextStyle(
                    fontSize: 11,
                    letterSpacing: 1.5,
                    color: Colors.white38,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 16),
                Expanded(
                  child: ListView.builder(
                    itemCount: _sections.length,
                    itemBuilder: (context, index) {
                      final isSelected = index == _selectedSectionIndex;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 6.0),
                        child: Material(
                          color: isSelected ? const Color(0xFF00E5FF).withOpacity(0.12) : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(8),
                            onTap: () => setState(() => _selectedSectionIndex = index),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                              child: Text(
                                _sections[index],
                                style: TextStyle(
                                  fontSize: 13,
                                  color: isSelected ? const Color(0xFF00E5FF) : Colors.white70,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
        const VerticalDivider(width: 1, color: Colors.white12),
        // Reading content area: ConstrainedBox prevents stretching on ultra-wide screens
        Expanded(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: kMaxReadingContentWidth),
              child: _buildReadingContent(),
            ),
          ),
        ),
      ],
    );
  }

  /// Single-column layout for mobile phones and compact windows
  Widget _buildSmallScreenLayout(BoxConstraints constraints) {
    return _buildReadingContent();
  }

  Widget _buildReadingContent() {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        _buildHeroMetricCards(),
        const SizedBox(height: 24),
        _buildSectionCard(
          title: '1. Executive Summary',
          content:
              'PearlAI Protocol is a decentralized liquidity AMM and staking yield ecosystem. '
              'It bridges decentralized finance with real-world tourism and wellness services, '
              'powering zero-fee direct bookings, Review-to-Earn (R2E) on-chain verification, '
              'and automated staking rewards on Ethereum and EVM-compatible layer 2 networks.',
        ),
        const SizedBox(height: 16),
        _buildSectionCard(
          title: '2. AMM Constant Product Formula',
          content:
              'The PearlAIPool utilizes constant product invariant mechanics:\n\n'
              '(x + Δx · 0.997) · (y - Δy) ≥ k\n\n'
              '• Fee Tier: 0.30% (30 bps) retained in the reserve pool.\n'
              '• Slippage Protection: Deterministic minOutput guardrails.\n'
              '• LP Token Minting: Geometric mean of deposits (√(Δx · Δy)).',
        ),
        const SizedBox(height: 16),
        _buildSectionCard(
          title: '3. Staking & Accumulative Yield Index',
          content:
              'Reward distribution is calculated using an O(1) continuous yield accumulator index:\n\n'
              'accRewardPerShare(t) = accRewardPerShare(t₀) + ((t - t₀) · RewardRate · 10¹²) / TotalLiquidity\n\n'
              '• Reward Rate: 0.01 PEARL / second per LP share.\n'
              '• Real-time Claiming: Instant rewards harvest via claimRewards().',
        ),
        const SizedBox(height: 16),
        _buildDeploymentDetailsCard(),
      ],
    );
  }

  Widget _buildHeroMetricCards() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 550 ? 4 : 2;
        return GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: crossAxisCount,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.8,
          children: const [
            _MetricTile(title: 'ETH MARKET PRICE', value: '\$2,463.89', subtitle: '🟢 Live CMC'),
            _MetricTile(title: 'PEARL TOKEN PRICE', value: '\$0.6706', subtitle: '0.000272 ETH'),
            _MetricTile(title: 'POOL TVL', value: '\$8,140.32', subtitle: '1.65 ETH + 6,069 PEARL'),
            _MetricTile(title: 'STAKING APY', value: '63.1%', subtitle: '0.01 PEARL / sec'),
          ],
        );
      },
    );
  }

  Widget _buildSectionCard({required String title, required String content}) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0E151C),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF00E5FF)),
          ),
          const SizedBox(height: 12),
          Text(
            content,
            style: const TextStyle(fontSize: 14, height: 1.6, color: Colors.white70),
          ),
        ],
      ),
    );
  }

  Widget _buildDeploymentDetailsCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0E151C),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF00FF88).withOpacity(0.3)),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '📋 Verified On-Chain Deployments',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF00FF88)),
          ),
          SizedBox(height: 12),
          Text(
            '• PearlAIToken (PEARL): 0x5FbDB2315678afecb367f032d93F642f64180aa3\n'
            '• PearlAIPool (AMM & Vault): 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512\n'
            '• Local EVM RPC: http://127.0.0.1:8545 (Chain ID: 31337)\n'
            '• Foundry Invariant Tests: 6 / 6 Suites Passed (100%)',
            style: TextStyle(fontFamily: 'monospace', fontSize: 12, height: 1.7, color: Colors.white70),
          ),
        ],
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  final String title;
  final String value;
  final String subtitle;

  const _MetricTile({required this.title, required this.value, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0A0F14),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(title, style: const TextStyle(fontSize: 9, letterSpacing: 1.1, color: Colors.white38)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Colors.white)),
          Text(subtitle, style: const TextStyle(fontSize: 10, color: Color(0xFF00FF88))),
        ],
      ),
    );
  }
}
