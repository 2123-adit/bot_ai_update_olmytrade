@extends('layouts.app')

@section('title', 'RODIS - Multi-Market Dashboard')

@section('styles')
    @include('dashboard.partials.styles')
@endsection

@section('content')
    <div id="main-banner" class="w-full h-screen relative group bg-gray-900 overflow-hidden shadow-xl mb-8 flex flex-col justify-end">
        <img src="{{ asset('assets/images/tembokratapan-solo.png') }}" alt="Banner Tembok Ratapan Solo"
            class="absolute inset-0 w-full h-full object-cover object-center transition-transform duration-1000 group-hover:scale-105 opacity-80">

        <div class="absolute inset-0 bg-gradient-to-t from-gray-50 via-black/50 to-transparent dark:from-[#0d1117]"></div>
    </div>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8 w-full relative z-20">
        @include('dashboard.sections.monitor')
        @include('dashboard.sections.detail')
        @include('dashboard.sections.rodis')
        @include('dashboard.sections.manual')
        @include('dashboard.sections.history')
    </div>
@endsection

@section('scripts')
    @include('dashboard.partials.scripts')
@endsection
