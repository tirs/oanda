import backtrader
import datetime
import os
import settings
import sys
import threading
import time

# Try to import curses, fallback to simple console UI on Windows
try:
    import curses
    CURSES_AVAILABLE = True
except ImportError:
    CURSES_AVAILABLE = False
    print("Curses not available (Windows), using simple console UI")

class CursedUI(object):
    def __init__(self, store):
        self.store = store
        self._heartbeatTime = ""
        self._instrument = ""
        self._account_currency = ""
        self._position = ""
        self._pricing = ""
        self._cash = ""
        self._leverage = ""
        self._exiting = False
        self.stdscr = None
        self.use_curses = CURSES_AVAILABLE

    def _update(self):
        try:
            self._instrument = str(self.store.get_instrument(settings.INSTRUMENT)['name'])
            self._account_currency = str(self.store.get_currency())
            self._position = str(self.store.get_positions())
            self._cash = str(self.store.get_value())
            self._leverage = str(self.store.get_leverage())

            _pricing = self.store.get_pricing(settings.INSTRUMENT)
            self._pricing = str(_pricing['bids'][0]['price'])+' bid, '+str(_pricing['asks'][0]['price'])+' ask'
            self._heartbeatTime = str(datetime.datetime.fromtimestamp(float(_pricing['time'])))
        except Exception as e:
            print(f"Error updating UI data: {e}")

    def start(self):
        if self.use_curses:
            try:
                # init curses
                self.stdscr = curses.initscr()
                curses.noecho()
                self.stdscr.keypad(1)
                self.stdscr.nodelay(1)
            except Exception as e:
                print(f"Failed to initialize curses: {e}")
                self.use_curses = False
        
        if not self.use_curses:
            print("Starting simple console UI...")
            print("Press Ctrl+C to exit")

    def stop(self):
        if self.use_curses and self.stdscr:
            try:
                # deinit curses
                self.stdscr.nodelay(0)
                self.stdscr.keypad(0)
                curses.echo()
                curses.endwin()
            except:
                pass
        
        try:
            self.store.stop()
        except:
            pass
        self._exiting = True

    def _threadfunc(self):
        try:
            while not self._exiting:
                self._update()
                self._render()
                if self.use_curses:
                    self._userinput()
                else:
                    time.sleep(1)  # Simple delay for console mode
        except KeyboardInterrupt:
            print("\nReceived Ctrl+C, exiting...")
        except Exception as e:
            print(f"Error in UI thread: {e}")
        finally:
            self.stop()
            os._exit(0)

    def _userinput(self):
        if not self.use_curses or not self.stdscr:
            return
        
        try:
            c = self.stdscr.getch()
            # q - quit
            if c == ord('q'):
                self.stdscr.addstr(14,0,"(now: quitting)",curses.A_STANDOUT)
                self.stdscr.refresh()
                self._exiting = True
        except:
            pass

    def _render(self):
        if self.use_curses and self.stdscr:
            self._render_curses()
        else:
            self._render_console()

    def _render_curses(self):
        try:
            self.stdscr.erase()
            self.stdscr.addstr(0,0,settings.BOT_NAME,curses.A_UNDERLINE)

            # Current account status
            self.stdscr.addstr(2,0,"Account currency:   "+self._account_currency)
            self.stdscr.addstr(3,0,"Trading instrument: "+self._instrument)

            # Ticker and heartbeat
            self.stdscr.addstr(5,0,"Heartbeat: "+self._heartbeatTime)
            self.stdscr.addstr(6,0,"Ticker:    "+str(self._pricing))

            # Account status
            self.stdscr.addstr(8, 0,"Position:        "+self._position)
            self.stdscr.addstr(11,0,"Cash:   "+self._cash)
            self.stdscr.addstr(12,0,"Leverage:       "+self._leverage)

            # Strategy status
            self.stdscr.addstr(13,0,"(Q)uit - exit")

            self.stdscr.refresh()
        except:
            pass

    def _render_console(self):
        """Simple console rendering for Windows"""
        try:
            # Clear screen (Windows compatible)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 60)
            print(f"🤖 {settings.BOT_NAME}")
            print("=" * 60)
            print(f"Account currency:   {self._account_currency}")
            print(f"Trading instrument: {self._instrument}")
            print()
            print(f"Heartbeat: {self._heartbeatTime}")
            print(f"Ticker:    {self._pricing}")
            print()
            print(f"Position:  {self._position}")
            print(f"Cash:      {self._cash}")
            print(f"Leverage:  {self._leverage}")
            print()
            print("Press Ctrl+C to exit")
            print("=" * 60)
        except Exception as e:
            print(f"Console render error: {e}")

    def run(self):
        self.start()
        self._thread = threading.Thread(target=self._threadfunc)
        self._thread.start()
