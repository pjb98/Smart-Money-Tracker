"""
Control Panel - Manage Trading Modes and System State
Switch between modes, enable/disable system, view status
"""
import argparse
from src.utils.trading_mode import TradingMode, get_mode_manager


def show_status():
    """Show current system status"""
    mode_manager = get_mode_manager()
    mode_manager.display_status()


def enable_system():
    """Enable the system"""
    mode_manager = get_mode_manager()
    mode_manager.enable()
    print("\n✅ System ENABLED")
    mode_manager.display_status()


def disable_system():
    """Disable the system"""
    mode_manager = get_mode_manager()
    mode_manager.disable()
    print("\n⏸️  System DISABLED")
    mode_manager.display_status()


def set_mode(mode_str: str, force: bool = False):
    """Set trading mode"""
    mode_manager = get_mode_manager()

    try:
        new_mode = TradingMode(mode_str.lower())
    except ValueError:
        print(f"\n❌ Invalid mode: {mode_str}")
        print(f"\nAvailable modes:")
        for mode in TradingMode:
            print(f"  - {mode.value}: {mode_manager.get_mode_description(mode)}")
        return

    # Validate transition
    current_mode = mode_manager.get_mode()
    is_valid, reason = mode_manager.validate_mode_transition(current_mode, new_mode)

    if not is_valid and not force:
        print(f"\n❌ Cannot switch to {new_mode.value}: {reason}")
        if new_mode == TradingMode.LIVE:
            print("\n💡 To enable live trading:")
            print("   1. Run: python control_panel.py --confirm-live")
            print("   2. Then: python control_panel.py --mode live")
        return

    # Set mode
    success = mode_manager.set_mode(new_mode, force=force)

    if success:
        print(f"\n✅ Mode changed to: {new_mode.value.upper()}")
        mode_manager.display_status()
    else:
        print(f"\n❌ Failed to change mode")


def confirm_live():
    """Confirm live trading mode"""
    mode_manager = get_mode_manager()

    print("\n" + "="*70)
    print("⚠️  LIVE TRADING CONFIRMATION ⚠️")
    print("="*70)
    print("\nYou are about to enable REAL trading with REAL money.")
    print("\n⚠️  RISKS:")
    print("  - You can LOSE money")
    print("  - Trades execute automatically")
    print("  - No undo button")
    print("  - Market volatility can cause losses")
    print("  - Smart contracts can have bugs")
    print("\n✅ BEFORE ENABLING:")
    print("  - Test thoroughly in paper trading mode")
    print("  - Understand all risks")
    print("  - Start with small position sizes")
    print("  - Set appropriate stop losses")
    print("  - Monitor actively")
    print("\n" + "="*70)

    response = input("\nType 'CONFIRM_LIVE' to enable live trading (or anything else to cancel): ")

    if response == "CONFIRM_LIVE":
        success = mode_manager.confirm_live_trading(response)
        if success:
            print("\n✅ Live trading CONFIRMED")
            print("   You can now switch to LIVE mode:")
            print("   python control_panel.py --mode live")
    else:
        print("\n❌ Live trading NOT confirmed. Smart move!")
        print("   Continue testing with paper trading.")


def emergency_stop():
    """Trigger emergency stop"""
    mode_manager = get_mode_manager()

    print("\n" + "="*70)
    print("🚨 EMERGENCY STOP 🚨")
    print("="*70)

    response = input("\nAre you sure you want to emergency stop? (yes/no): ")

    if response.lower() == 'yes':
        mode_manager.emergency_stop("Manual emergency stop via control panel")
        print("\n✅ Emergency stop activated")
        print("   System is now DISABLED")
    else:
        print("\n❌ Emergency stop cancelled")


def list_modes():
    """List all available modes"""
    mode_manager = get_mode_manager()

    print("\n" + "="*70)
    print("AVAILABLE TRADING MODES")
    print("="*70)

    for mode in TradingMode:
        description = mode_manager.get_mode_description(mode)
        emoji = {
            TradingMode.OFF: '⚫',
            TradingMode.OBSERVATION: '👁️ ',
            TradingMode.PAPER_TRADING: '📄',
            TradingMode.TRAINING: '🎓',
            TradingMode.TRAINING_PAPER: '🎓📄',
            TradingMode.LIVE: '🔴'
        }.get(mode, '❓')

        print(f"\n{emoji} {mode.value.upper()}")
        print(f"   {description}")

        # Add usage hints
        if mode == TradingMode.OBSERVATION:
            print(f"   → Use for: Watching and learning without trading")
        elif mode == TradingMode.PAPER_TRADING:
            print(f"   → Use for: Testing strategies with virtual capital")
        elif mode == TradingMode.TRAINING:
            print(f"   → Use for: Backtesting on historical data")
        elif mode == TradingMode.TRAINING_PAPER:
            print(f"   → Use for: Learning + simulating paper trades")
        elif mode == TradingMode.LIVE:
            print(f"   → Use for: Real trading (requires confirmation)")

    print("\n" + "="*70)

    print("\n💡 Quick Commands:")
    print("   python control_panel.py --mode observation")
    print("   python control_panel.py --mode paper_trading")
    print("   python control_panel.py --mode training")
    print("   python control_panel.py --enable")
    print("   python control_panel.py --disable")


def reset_daily():
    """Reset daily statistics"""
    mode_manager = get_mode_manager()
    mode_manager.reset_daily_stats()
    print("\n✅ Daily statistics reset")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Control Panel - Manage trading modes and system state',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View status
  python control_panel.py --status

  # Enable/disable system
  python control_panel.py --enable
  python control_panel.py --disable

  # Switch modes
  python control_panel.py --mode observation
  python control_panel.py --mode paper_trading
  python control_panel.py --mode training

  # Enable live trading (requires confirmation)
  python control_panel.py --confirm-live
  python control_panel.py --mode live

  # Emergency stop
  python control_panel.py --emergency-stop
        """
    )

    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--enable', action='store_true', help='Enable system')
    parser.add_argument('--disable', action='store_true', help='Disable system')
    parser.add_argument('--mode', type=str, help='Set trading mode')
    parser.add_argument('--force', action='store_true', help='Force mode change (skip validation)')
    parser.add_argument('--list-modes', action='store_true', help='List all available modes')
    parser.add_argument('--confirm-live', action='store_true', help='Confirm live trading')
    parser.add_argument('--emergency-stop', action='store_true', help='Emergency stop')
    parser.add_argument('--reset-daily', action='store_true', help='Reset daily statistics')

    args = parser.parse_args()

    # If no args, show status
    if not any(vars(args).values()):
        show_status()
        print("\n💡 Use --help for all options")
        return

    # Handle commands
    if args.status:
        show_status()

    elif args.enable:
        enable_system()

    elif args.disable:
        disable_system()

    elif args.mode:
        set_mode(args.mode, force=args.force)

    elif args.list_modes:
        list_modes()

    elif args.confirm_live:
        confirm_live()

    elif args.emergency_stop:
        emergency_stop()

    elif args.reset_daily:
        reset_daily()


if __name__ == "__main__":
    main()
