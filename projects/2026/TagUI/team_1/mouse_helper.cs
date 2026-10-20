using System;
using System.Diagnostics;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

public class MouseHelper {
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("user32.dll")]
    public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder lpClassName, int nMaxCount);

    public const int MOUSEEVENTF_LEFTDOWN = 0x02;
    public const int MOUSEEVENTF_LEFTUP = 0x04;
    public const int MOUSEEVENTF_RIGHTDOWN = 0x08;
    public const int MOUSEEVENTF_RIGHTUP = 0x10;
    public const int MOUSEEVENTF_WHEEL = 0x0800;

    public const int SW_RESTORE = 9;
    public const int SW_MAXIMIZE = 3;

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public static POINT GetPosition() {
        POINT p;
        GetCursorPos(out p);
        return p;
    }

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("kernel32.dll")]
    public static extern uint GetCurrentThreadId();

    [DllImport("user32.dll")]
    public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    public static IntPtr GetChromeHwnd(int targetPid = 0) {
        IntPtr found = IntPtr.Zero;
        try {
            EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
                System.Text.StringBuilder sb = new System.Text.StringBuilder(256);
                GetClassName(hWnd, sb, sb.Capacity);
                if (sb.ToString() == "Chrome_WidgetWin_1") {
                    if (targetPid > 0) {
                        uint pid = 0;
                        GetWindowThreadProcessId(hWnd, out pid);
                        if (pid != (uint)targetPid) {
                            return true; // Sigue buscando la ventana con el PID específico
                        }
                    }
                    RECT r;
                    if (GetWindowRect(hWnd, out r)) {
                        int w = r.Right - r.Left;
                        int h = r.Bottom - r.Top;
                        // Si buscamos por PID o si es una ventana visible estándar
                        if (targetPid > 0 || (w >= 400 && h >= 300)) {
                            found = hWnd;
                            return false; // Encontrada
                        }
                    }
                }
                return true;
            }, IntPtr.Zero);
        } catch {}
        return found;
    }

    public static IntPtr FindChromeHwndWithRetry(int targetPid = 0, int maxWaitMs = 2500) {
        int elapsed = 0;
        while (elapsed < maxWaitMs) {
            IntPtr hwnd = GetChromeHwnd(targetPid);
            if (hwnd != IntPtr.Zero) return hwnd;
            Thread.Sleep(100);
            elapsed += 100;
        }
        return GetChromeHwnd(0); // Fallback a cualquier ventana de Chrome
    }

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetThreadDesktop(IntPtr hDesktop);

    public static void AttachToDefaultDesktop() {
        try {
            IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
            if (hDesk != IntPtr.Zero) {
                SetThreadDesktop(hDesk);
            }
        } catch {}
    }

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    public const int KEYEVENTF_KEYUP = 0x0002;
    public const byte VK_MENU = 0x12;

    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsZoomed(IntPtr hWnd);

    public static bool FocusChrome(int targetPid = 0) {
        try {
            AttachToDefaultDesktop();
            IntPtr hwnd = FindChromeHwndWithRetry(targetPid, 2000);
            if (hwnd != IntPtr.Zero) {
                // 1. Des-minimizar ÚNICAMENTE si la ventana se encuentra minimizada (evita achicar ventanas maximizadas)
                if (IsIconic(hwnd)) {
                    ShowWindow(hwnd, SW_RESTORE);
                    Thread.Sleep(60);
                }

                // 2. Maximizar a pantalla completa ÚNICAMENTE si no está ya maximizada
                if (!IsZoomed(hwnd)) {
                    ShowWindow(hwnd, SW_MAXIMIZE);
                    Thread.Sleep(60);
                }

                // 3. Traer al frente saltando la restricción ForegroundLockTimeout de Windows
                IntPtr foreWnd = GetForegroundWindow();
                uint dummyPid;
                uint foreThread = GetWindowThreadProcessId(foreWnd, out dummyPid);
                uint curThread = GetCurrentThreadId();
                bool attached = false;
                if (foreThread != 0 && foreThread != curThread) {
                    attached = AttachThreadInput(curThread, foreThread, true);
                }

                BringWindowToTop(hwnd);
                SetForegroundWindow(hwnd);

                if (attached) {
                    AttachThreadInput(curThread, foreThread, false);
                }

                // 4. Liberar bloqueo de foco con tecla ALT
                keybd_event(VK_MENU, 0, 0, UIntPtr.Zero);
                keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                SetForegroundWindow(hwnd);

                Thread.Sleep(60);
                return true;
            }
        } catch {}
        return false;
    }

    public static string StateFilePath = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "failsafe.state");
    public static string FlagFilePath = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "failsafe.flag");

    public static void SetFailsafeState(bool isMoving, int x, int y) {
        try {
            using (var fs = new System.IO.FileStream(StateFilePath, System.IO.FileMode.Create, System.IO.FileAccess.Write, System.IO.FileShare.ReadWrite))
            using (var sw = new System.IO.StreamWriter(fs)) {
                sw.Write((isMoving ? "1" : "0") + "," + x + "," + y);
            }
        } catch {}
    }

    public static void TriggerFailsafe(int x, int y) {
        try {
            using (var fs = new System.IO.FileStream(FlagFilePath, System.IO.FileMode.Create, System.IO.FileAccess.Write, System.IO.FileShare.ReadWrite))
            using (var sw = new System.IO.StreamWriter(fs)) {
                sw.Write("USER_MOUSE_INTERVENTION," + x + "," + y);
            }
        } catch {}
        Console.WriteLine("USER_MOUSE_INTERVENTION");
        Environment.Exit(99);
    }

    public static void RunWatchdog() {
        AttachToDefaultDesktop();
        if (System.IO.File.Exists(FlagFilePath)) {
            try { System.IO.File.Delete(FlagFilePath); } catch {}
        }

        POINT initPos = GetPosition();
        SetFailsafeState(false, initPos.X, initPos.Y);

        int consecutiveViolations = 0;
        const int REQUIRED_CONSECUTIVE_VIOLATIONS = 4; // Requiere ~160ms sostenidos de desvío brusco

        while (true) {
            Thread.Sleep(40);
            POINT cur = GetPosition();

            bool isMoving = false;
            int expX = cur.X, expY = cur.Y;

            if (System.IO.File.Exists(StateFilePath)) {
                try {
                    using (var fs = new System.IO.FileStream(StateFilePath, System.IO.FileMode.Open, System.IO.FileAccess.Read, System.IO.FileShare.ReadWrite))
                    using (var sr = new System.IO.StreamReader(fs)) {
                        string content = sr.ReadToEnd().Trim();
                        string[] parts = content.Split(',');
                        if (parts.Length >= 3) {
                            isMoving = parts[0] == "1";
                            expX = int.Parse(parts[1]);
                            expY = int.Parse(parts[2]);
                        }
                    }
                } catch {}
            }

            double dist = Math.Sqrt(Math.Pow(cur.X - expX, 2) + Math.Pow(cur.Y - expY, 2));

            // Umbrales calibrados para movimiento deliberado y brusco:
            // - En movimiento del bot: > 320px
            // - En reposo/pausas del bot: > 260px
            double threshold = isMoving ? 320.0 : 260.0;

            if (dist > threshold) {
                consecutiveViolations++;
                if (consecutiveViolations >= REQUIRED_CONSECUTIVE_VIOLATIONS) {
                    TriggerFailsafe(cur.X, cur.Y);
                    return;
                }
            } else {
                // Si la distancia está dentro de lo normal, reseteamos el contador
                consecutiveViolations = 0;
            }
        }
    }

    // Movimiento con curvas de Bézier cúbicas y aceleración/desaceleración humana
    public static void MoveSmooth(int targetX, int targetY, int durationMs) {
        POINT start = GetPosition();
        if (start.X == targetX && start.Y == targetY) {
            SetFailsafeState(false, targetX, targetY);
            return;
        }

        SetFailsafeState(true, start.X, start.Y);

        if (durationMs <= 30) {
            SetCursorPos(targetX, targetY);
            SetFailsafeState(false, targetX, targetY);
            return;
        }

        Random rnd = new Random();
        double distance = Math.Sqrt(Math.Pow(targetX - start.X, 2) + Math.Pow(targetY - start.Y, 2));
        double deviation = Math.Min(distance * 0.25, 120.0);

        // Control points para curva cúbica de Bézier
        double cp1X = start.X + (targetX - start.X) * 0.25 + (rnd.NextDouble() - 0.5) * deviation;
        double cp1Y = start.Y + (targetY - start.Y) * 0.25 + (rnd.NextDouble() - 0.5) * deviation;
        double cp2X = start.X + (targetX - start.X) * 0.75 + (rnd.NextDouble() - 0.5) * deviation;
        double cp2Y = start.Y + (targetY - start.Y) * 0.75 + (rnd.NextDouble() - 0.5) * deviation;

        int steps = Math.Max((int)(durationMs / 12), 18);
        int sleepPerStep = Math.Max(durationMs / steps, 8);
        int lastSetX = start.X;
        int lastSetY = start.Y;
        int inFlightDeviations = 0;

        for (int i = 1; i <= steps; i++) {
            // Regla: Detección de intervención física brusca del usuario durante el movimiento
            POINT current = GetPosition();
            double userDeviation = Math.Sqrt(Math.Pow(current.X - lastSetX, 2) + Math.Pow(current.Y - lastSetY, 2));
            if (i > 1 && userDeviation > 280.0) {
                inFlightDeviations++;
                if (inFlightDeviations >= 2) {
                    TriggerFailsafe(current.X, current.Y);
                    return;
                }
            } else {
                inFlightDeviations = 0;
            }

            double tLinear = (double)i / steps;
            double t = tLinear < 0.5 
                ? 4.0 * tLinear * tLinear * tLinear 
                : 1.0 - Math.Pow(-2.0 * tLinear + 2.0, 3.0) / 2.0;

            double u = 1.0 - t;
            double tt = t * t;
            double uu = u * u;
            double uuu = uu * u;
            double ttt = tt * t;

            double px = uuu * start.X + 3 * uu * t * cp1X + 3 * u * tt * cp2X + ttt * targetX;
            double py = uuu * start.Y + 3 * uu * t * cp1Y + 3 * u * tt * cp2Y + ttt * targetY;

            lastSetX = (int)Math.Round(px);
            lastSetY = (int)Math.Round(py);
            SetFailsafeState(true, lastSetX, lastSetY);
            SetCursorPos(lastSetX, lastSetY);
            Thread.Sleep(sleepPerStep);
        }

        SetCursorPos(targetX, targetY);
        SetFailsafeState(false, targetX, targetY);
        Thread.Sleep(50);
    }

    // Clic humano visible con pausa realista entre down y up
    public static void Click(int? x, int? y, int durationMs = 400) {
        if (x.HasValue && y.HasValue) {
            MoveSmooth(x.Value, y.Value, durationMs);
        }
        Thread.Sleep(100);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(110);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
        Thread.Sleep(120);
        POINT p = GetPosition();
        SetFailsafeState(false, p.X, p.Y);
    }

    // Convierte coordenadas CSS del viewport al escritorio físico. Puppeteer sólo
    // lee la posición; el movimiento y el click se realizan con Win32 reales.
    public static POINT ViewportToScreen(int x, int y, int outerWidth, int outerHeight, int innerWidth, int innerHeight) {
        IntPtr hwnd = GetChromeHwnd();
        RECT rect;
        if (hwnd == IntPtr.Zero || !GetWindowRect(hwnd, out rect)) return new POINT { X = x, Y = y };

        double windowWidth = Math.Max(1, rect.Right - rect.Left);
        double scale = outerWidth > 0 ? windowWidth / outerWidth : 1.0;
        double contentWidth = Math.Max(1, innerWidth * scale);
        double contentHeight = Math.Max(1, innerHeight * scale);
        double contentLeft = rect.Left + Math.Max(0, (windowWidth - contentWidth) / 2.0);
        double contentTop = rect.Bottom - contentHeight;
        return new POINT {
            X = (int)Math.Round(contentLeft + x * scale),
            Y = (int)Math.Round(contentTop + y * scale)
        };
    }

    public static void MoveViewport(int x, int y, int outerWidth, int outerHeight, int innerWidth, int innerHeight, int durationMs) {
        FocusChrome();
        POINT screenPoint = ViewportToScreen(x, y, outerWidth, outerHeight, innerWidth, innerHeight);
        MoveSmooth(screenPoint.X, screenPoint.Y, durationMs);
    }

    public static void ClickViewport(int x, int y, int outerWidth, int outerHeight, int innerWidth, int innerHeight, int durationMs) {
        MoveViewport(x, y, outerWidth, outerHeight, innerWidth, innerHeight, durationMs);
        Click(null, null, 0);
    }

    // pixels positivos representan un desplazamiento hacia abajo, como la rueda.
    public static void ScrollVisible(int pixels, int steps, int delayMs) {
        FocusChrome();
        POINT p = GetPosition();
        SetFailsafeState(false, p.X, p.Y);
        int count = Math.Max(1, Math.Abs(pixels) / Math.Max(1, steps * 90));
        int direction = pixels >= 0 ? -120 : 120;
        for (int i = 0; i < count; i++) {
            mouse_event(MOUSEEVENTF_WHEEL, 0, 0, direction, 0);
            Thread.Sleep(Math.Max(delayMs, 40));
        }
        POINT pEnd = GetPosition();
        SetFailsafeState(false, pEnd.X, pEnd.Y);
    }

    // Arrastre fluido de sliders y rangos
    public static void Drag(int x1, int y1, int x2, int y2, int durationMs) {
        MoveSmooth(x1, y1, 400);
        Thread.Sleep(120);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(150);
        MoveSmooth(x2, y2, durationMs);
        Thread.Sleep(150);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
        Thread.Sleep(120);
        POINT p = GetPosition();
        SetFailsafeState(false, p.X, p.Y);
    }

    // Escritura progresiva letra por letra visible (sin utilizar clipboard)
    public static void TypeText(string text, int charDelayMs) {
        if (string.IsNullOrEmpty(text)) return;
        POINT p = GetPosition();
        SetFailsafeState(false, p.X, p.Y);
        foreach (char c in text) {
            string s = c.ToString();
            try {
                if (s == "{" || s == "}" || s == "(" || s == ")" || s == "+" || s == "^" || s == "%" || s == "~") {
                    SendKeys.SendWait("{" + s + "}");
                } else {
                    SendKeys.SendWait(s);
                }
            } catch {
                try {
                    SendKeys.SendWait(s);
                } catch {}
            }
            Thread.Sleep(Math.Max(charDelayMs, 15));
        }
        POINT pEnd = GetPosition();
        SetFailsafeState(false, pEnd.X, pEnd.Y);
    }

    // Navegación 100% VISIBLE por la barra de direcciones de Chrome:
    // 1. Foco en Chrome -> 2. Mover mouse a Omnibox -> 3. Click real -> 4. Ctrl+L para seleccionar todo -> 5. Pausa -> 6. Tipeo carácter por carácter -> 7. Enter
    public static void NavigateOmnibox(string url, int typingDelayMs) {
        // 1. Llevar Chrome al frente
        FocusChrome();
        Thread.Sleep(200);

        IntPtr hwnd = GetChromeHwnd();
        int targetX = 500;
        int targetY = 55;

        if (hwnd != IntPtr.Zero) {
            RECT rect;
            GetWindowRect(hwnd, out rect);
            int winWidth = Math.Max(100, rect.Right - rect.Left);
            targetX = rect.Left + Math.Min(600, Math.Max(winWidth / 4, winWidth / 2));
            targetY = Math.Max(50, rect.Top + 55);
        }

        // 2. Mover físicamente el mouse hacia la barra de direcciones
        MoveSmooth(targetX, targetY, 450);
        Thread.Sleep(100);

        // 3. Hacer click real sobre la barra para activar el foco
        Click(targetX, targetY, 150);
        Thread.Sleep(150);

        // 4. Utilizar Ctrl+L o Alt+D para seleccionar TODA la URL actual
        try {
            SendKeys.SendWait("^l");
        } catch {
            try {
                SendKeys.SendWait("%d");
            } catch {}
        }

        // 5. Esperar unos milisegundos para asegurar la selección (NO hacer un segundo click después de esto)
        Thread.Sleep(180);

        // 6. Escribir la nueva URL carácter por carácter (reemplaza visualmente la selección anterior)
        TypeText(url, typingDelayMs);
        Thread.Sleep(150);

        // 7. Presionar Enter para iniciar la navegación
        try {
            SendKeys.SendWait("{ENTER}");
        } catch {}

        POINT finalPos = GetPosition();
        SetFailsafeState(false, finalPos.X, finalPos.Y);
    }

    [STAThread]
    public static void Main(string[] args) {
        try {
            SetProcessDPIAware();
        } catch {}

        Thread t = new Thread(() => {
            AttachToDefaultDesktop();
            Run(args);
        });
        t.SetApartmentState(ApartmentState.STA);
        t.Start();
        t.Join();
    }

    public static void Run(string[] args) {
        if (args.Length == 0) {
            Console.WriteLine("MouseHelper v2.0 - Windows Native Cursor & Automation Controller");
            Console.WriteLine("Usage: mouse_helper <cmd> [args...]");
            Console.WriteLine("Commands:");
            Console.WriteLine("  pos                           -> prints current x,y");
            Console.WriteLine("  move <x> <y> [ms]             -> moves cursor smoothly");
            Console.WriteLine("  click [x y] [ms]              -> clicks at current or target position");
            Console.WriteLine("  moveviewport <x> <y> <outerW> <outerH> <innerW> <innerH> [ms]");
            Console.WriteLine("  clickviewport <x> <y> <outerW> <outerH> <innerW> <innerH> [ms]");
            Console.WriteLine("  scroll <pixels> [steps] [ms]  -> native wheel scroll (positive = down)");
            Console.WriteLine("  drag <x1> <y1> <x2> <y2> [ms] -> drag & drop");
            Console.WriteLine("  type <text> [charDelayMs]     -> types progressive text");
            Console.WriteLine("  key <keys>                    -> sends special keys (e.g. {ENTER})");
            Console.WriteLine("  nav <url> [charDelayMs]       -> visible move to omnibox, clicks, types url, hits Enter");
            Console.WriteLine("  focus                         -> brings Chrome to front");
            return;
        }

        string cmd = args[0].ToLowerInvariant();

        try {
            switch (cmd) {
                case "watchdog": {
                    RunWatchdog();
                    break;
                }
                case "pos": {
                    POINT p = GetPosition();
                    Console.WriteLine(p.X + "," + p.Y);
                    break;
                }
                case "move": {
                    int x = int.Parse(args[1]);
                    int y = int.Parse(args[2]);
                    int ms = args.Length > 3 ? int.Parse(args[3]) : 500;
                    MoveSmooth(x, y, ms);
                    Console.WriteLine("OK");
                    break;
                }
                case "click": {
                    if (args.Length >= 3) {
                        int x = int.Parse(args[1]);
                        int y = int.Parse(args[2]);
                        int ms = args.Length > 3 ? int.Parse(args[3]) : 400;
                        Click(x, y, ms);
                    } else {
                        Click(null, null);
                    }
                    Console.WriteLine("OK");
                    break;
                }
                case "moveviewport": {
                    int ms = args.Length > 7 ? int.Parse(args[7]) : 500;
                    MoveViewport(int.Parse(args[1]), int.Parse(args[2]), int.Parse(args[3]), int.Parse(args[4]), int.Parse(args[5]), int.Parse(args[6]), ms);
                    Console.WriteLine("OK");
                    break;
                }
                case "clickviewport": {
                    int ms = args.Length > 7 ? int.Parse(args[7]) : 0;
                    ClickViewport(int.Parse(args[1]), int.Parse(args[2]), int.Parse(args[3]), int.Parse(args[4]), int.Parse(args[5]), int.Parse(args[6]), ms);
                    Console.WriteLine("OK");
                    break;
                }
                case "scroll": {
                    int steps = args.Length > 2 ? int.Parse(args[2]) : 1;
                    int delay = args.Length > 3 ? int.Parse(args[3]) : 100;
                    ScrollVisible(int.Parse(args[1]), steps, delay);
                    Console.WriteLine("OK");
                    break;
                }
                case "drag": {
                    int x1 = int.Parse(args[1]);
                    int y1 = int.Parse(args[2]);
                    int x2 = int.Parse(args[3]);
                    int y2 = int.Parse(args[4]);
                    int ms = args.Length > 5 ? int.Parse(args[5]) : 600;
                    Drag(x1, y1, x2, y2, ms);
                    Console.WriteLine("OK");
                    break;
                }
                case "type": {
                    string text = args[1];
                    int delay = args.Length > 2 ? int.Parse(args[2]) : 50;
                    TypeText(text, delay);
                    Console.WriteLine("OK");
                    break;
                }
                case "key": {
                    string keys = args[1];
                    SendKeys.SendWait(keys);
                    Console.WriteLine("OK");
                    break;
                }
                case "nav": {
                    string url = args[1];
                    int delay = args.Length > 2 ? int.Parse(args[2]) : 45;
                    NavigateOmnibox(url, delay);
                    Console.WriteLine("OK");
                    break;
                }
                case "focus": {
                    int targetPid = 0;
                    if (args.Length > 1) int.TryParse(args[1], out targetPid);
                    bool ok = FocusChrome(targetPid);
                    Console.WriteLine(ok ? "OK" : "NOT_FOUND");
                    break;
                }
                case "closetab": {
                    int targetPid = 0;
                    if (args.Length > 1) int.TryParse(args[1], out targetPid);
                    FocusChrome(targetPid);
                    Thread.Sleep(80);
                    SendKeys.SendWait("^w");
                    Console.WriteLine("OK");
                    break;
                }
                case "delayedclosetab": {
                    int delayMs = 1500;
                    if (args.Length > 1) {
                        int parsedSec = 1;
                        if (int.TryParse(args[1], out parsedSec)) {
                            delayMs = parsedSec * 1000;
                        }
                    }
                    try {
                        ProcessStartInfo psi = new ProcessStartInfo();
                        psi.FileName = System.Reflection.Assembly.GetExecutingAssembly().Location;
                        psi.Arguments = "closetab_worker " + delayMs;
                        psi.UseShellExecute = true;
                        psi.CreateNoWindow = true;
                        psi.WindowStyle = ProcessWindowStyle.Hidden;
                        Process.Start(psi);
                    } catch {}
                    Console.WriteLine("OK");
                    break;
                }
                case "closetab_worker": {
                    int delayMs = 1500;
                    if (args.Length > 1) int.TryParse(args[1], out delayMs);
                    Thread.Sleep(delayMs);
                    try {
                        FocusChrome(0);
                        Thread.Sleep(100);
                        SendKeys.SendWait("^w");
                        Thread.Sleep(400);
                        foreach (var proc in System.Diagnostics.Process.GetProcessesByName("chrome")) {
                            try { proc.Kill(); } catch {}
                        }
                    } catch {}
                    break;
                }
                case "close": {
                    int targetPid = 0;
                    if (args.Length > 1) int.TryParse(args[1], out targetPid);
                    FocusChrome(targetPid);
                    Thread.Sleep(80);
                    SendKeys.SendWait("%{F4}");
                    Console.WriteLine("OK");
                    break;
                }
                default: {
                    Console.WriteLine("UNKNOWN_CMD");
                    break;
                }
            }
        } catch (Exception ex) {
            Console.Error.WriteLine("ERROR: " + ex.Message);
        }
    }
}
