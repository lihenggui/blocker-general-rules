
rootProject.name = "SummaryGenerator"

dependencyResolutionManagement {
    versionCatalogs {
        create("libs") {
            library("kotlinx-serialization-json", "org.jetbrains.kotlinx:kotlinx-serialization-json:1.4.1")
        }
    }
}

