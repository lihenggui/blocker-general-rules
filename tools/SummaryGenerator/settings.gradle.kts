
rootProject.name = "SummaryGenerator"

dependencyResolutionManagement {
    versionCatalogs {
        create("libs") {
            library("kotlinx-serialization-json", "org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0-RC")
            library("apache-common-io", "commons-io:commons-io:2.13.0")
        }
    }
}

