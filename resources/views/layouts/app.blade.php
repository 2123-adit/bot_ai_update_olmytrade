<!DOCTYPE html>
<html lang="id">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'RODIS - Robot Trading')</title>

    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js"></script>

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif']
                    },
                    colors: {
                        gojek: {
                            DEFAULT: '#00aa13',
                            dark: '#00880f',
                            light: '#e6f6e8'
                        },
                        red: {
                            DEFAULT: '#ee2737',
                            dark: '#c81d28',
                            light: '#fdedee'
                        },
                        dark: '#1c1c1c',
                        graybg: '#f4f5f7'
                    }
                }
            }
        }

        // Deteksi IP/Domain VPS otomatis untuk menghubungi Python di port 5000
        if (typeof API_BASE === 'undefined') {
            var API_BASE = window.location.protocol + "//" + window.location.hostname + ":5000/api";
        }
    </script>

    <style>
        body {
            background-color: #f4f5f7;
        }

        ::-webkit-scrollbar {
            width: 6px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #9ca3af;
        }
    </style>

    @yield('styles')
</head>

<body class="text-dark antialiased flex flex-col min-h-screen">

    @include('dashboard.partials.navbar')

    <main class="flex-grow">
        @yield('content')
    </main>

    @include('dashboard.partials.footer')

    <!-- ✅ GLOBAL POPUP CONTAINER -->
    <div id="popup-container" class="fixed top-5 right-5 z-50 space-y-3 pointer-events-none">
    </div>

    @yield('scripts')

</body>

</html>