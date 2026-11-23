package dev.wknd.demo.weather;

public record Weather(String location, double temperature, double humidity,
                      double wind, String condition, String source, String time) {}
