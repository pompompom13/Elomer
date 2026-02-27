"""
Логика расчета с учетом плотности врачей и территориального деления
"""

import random
import numpy as np
import math
from datetime import datetime, timedelta


class DensityCalculator:
    """Калькулятор, учитывающий плотность врачей и территориальное деление"""

    def __init__(self, cities_data):
        self.cities_data = cities_data

    def calculate_density_factors(self, city, specialization):
        """Рассчитывает факторы плотности для города и специализации"""
        city_data = self.cities_data.get(city, {})
        if not city_data:
            return None

        # Определяем ключ специализации
        spec_key = None
        spec_lower = specialization.lower()
        if 'кардиолог' in spec_lower:
            spec_key = 'cardio'
        elif 'терапевт' in spec_lower:
            spec_key = 'therapy'
        elif 'педиатр' in spec_lower:
            spec_key = 'pediatric'
        elif 'аптек' in spec_lower:
            spec_key = 'pharmacy'
        else:
            spec_key = 'therapy'  # По умолчанию

        # Плотность врачей в поликлинике (врачей на поликлинику)
        doctors_per_clinic = city_data['doctors_per_polyclinic'].get(spec_key, 2)

        return {
            'doctors_per_clinic': doctors_per_clinic,
            'same_clinic_probability': city_data.get('same_clinic_probability', 0.5),
            'waiting_time_range': city_data.get('waiting_time_range', (5, 20)),
            'doctor_absence_probability': city_data.get('doctor_absence_probability', 0.15),
            'districts': city_data.get('districts', 1),
            'city_area_km2': city_data.get('city_area_km2', 100),
            'polyclinics': city_data.get('polyclinics', 50),
            'avg_distance_km': city_data.get('avg_distance_km', 3.5),
            'spec_key': spec_key
        }

    def simulate_density_day(self, city, specialization, target_visits, transport_type):
        """
        Симуляция дня с учётом плотности врачей и ТЕРРИТОРИАЛЬНОГО ДЕЛЕНИЯ
        В больших городах медпред работает только в 1-2 районах!
        """
        density_factors = self.calculate_density_factors(city, specialization)
        if not density_factors:
            return self._fallback_calculation(city, specialization, target_visits, transport_type)

        # ★ КЛЮЧЕВОЙ ПРИНЦИП: в крупных городах ограничиваемся 1-2 районами ★
        is_big_city = city in ['Москва', 'Санкт-Петербург']
        if is_big_city:
            max_districts = 2  # В Москве/Питере максимум 2 района в день
            clinics_per_district = density_factors['polyclinics'] // density_factors['districts']
            avg_distance_within_district = 1.5  # км внутри района
            avg_distance_between_districts = 8.0  # км между районами
        elif density_factors['districts'] >= 5:
            max_districts = 3  # В крупных городах 2-3 района
            clinics_per_district = density_factors['polyclinics'] // density_factors['districts']
            avg_distance_within_district = 2.0
            avg_distance_between_districts = 5.0
        else:
            max_districts = min(3, density_factors['districts'])  # В маленьких можно все
            clinics_per_district = density_factors['polyclinics']
            avg_distance_within_district = 3.0
            avg_distance_between_districts = 4.0

        # ★ ВЫБИРАЕМ РАЙОНЫ ДЛЯ ЭТОГО ДНЯ ★
        available_districts = random.sample(
            range(1, density_factors['districts'] + 1),
            min(max_districts, density_factors['districts'])
        )

        # ★ ВИЗИТЫ В ОДНОЙ ПОЛИКЛИНИКЕ ★
        doctors_per_clinic = density_factors['doctors_per_clinic']
        same_clinic_prob = density_factors['same_clinic_probability']

        schedule = []
        remaining_visits = target_visits
        current_district = random.choice(available_districts)
        visited_clinics_by_district = {d: set() for d in available_districts}
        total_travel_distance = 0

        transport_speed = {'Автомобиль': 40, 'Общественный транспорт': 25, 'Пешком': 5}.get(transport_type, 40)
        transport_waiting = {'Автомобиль': 5, 'Общественный транспорт': 10, 'Пешь': 0}.get(transport_type, 5)

        while remaining_visits > 0:
            # ★ РЕШАЕМ: остаться в той же поликлинике или поехать в другую? ★
            current_clinics = visited_clinics_by_district[current_district]

            if current_clinics and random.random() < same_clinic_prob * 0.7:
                # Возвращаемся в уже посещенную поликлинику (другие врачи/смена)
                clinic_id = random.choice(list(current_clinics))
                travel_distance = 0  # Уже там
                same_clinic_return = True
            else:
                # Идем в новую поликлинику
                clinic_id = len(current_clinics) + 1
                current_clinics.add(clinic_id)

                # Расстояние зависит от того, меняем ли район
                if not visited_clinics_by_district[current_district] or len(
                        visited_clinics_by_district[current_district]) == 1:
                    travel_distance = 0  # Первая поликлиника в районе
                else:
                    # Внутри района - близко, между районами - дальше
                    if random.random() < 0.8 or len(available_districts) == 1:
                        # Остаемся в том же районе (80% времени)
                        travel_distance = avg_distance_within_district * random.uniform(0.5, 1.5)
                    else:
                        # Меняем район (20% времени, только если есть куда менять)
                        old_district = current_district
                        current_district = random.choice([d for d in available_districts if d != old_district])
                        travel_distance = avg_distance_between_districts * random.uniform(0.8, 1.2)

            total_travel_distance += travel_distance

            # ★ СКОЛЬКО ВРАЧЕЙ ДОСТУПНО В ЭТОЙ ПОЛИКЛИНИКЕ СЕЙЧАС? ★
            # Учитываем смены: утро (3-5 врачей), день (4-6), вечер (2-4)
            time_of_day = 'morning' if len(schedule) < target_visits * 0.4 else \
                'afternoon' if len(schedule) < target_visits * 0.7 else 'evening'

            if time_of_day == 'morning':
                available_doctors_now = max(1, int(doctors_per_clinic * random.uniform(0.3, 0.5)))
            elif time_of_day == 'afternoon':
                available_doctors_now = max(1, int(doctors_per_clinic * random.uniform(0.4, 0.6)))
            else:  # evening
                available_doctors_now = max(1, int(doctors_per_clinic * random.uniform(0.2, 0.4)))

            # ★ СКОЛЬКО ВИЗИТОВ СДЕЛАЕМ ЗА ЭТОТ ЗАХОД? ★
            # За один заход можно посетить 1-3 врачей максимум
            max_visits_per_visit = min(3, available_doctors_now)
            visits_this_time = min(
                remaining_visits,
                random.randint(1, max_visits_per_visit)
            )

            for visit_num in range(visits_this_time):
                # Время ожидания зависит от времени дня
                if time_of_day == 'morning':
                    waiting_time = random.uniform(10, 25)  # Утром больше очередь
                elif time_of_day == 'afternoon':
                    waiting_time = random.uniform(5, 15)  # Днем меньше
                else:
                    waiting_time = random.uniform(15, 30)  # Вечером врачей мало

                # Вероятность отсутствия врача
                if random.random() < density_factors['doctor_absence_probability']:
                    # Неудачный визит - врач отсутствует
                    visit_duration = waiting_time
                    successful = False
                else:
                    # Успешный визит
                    if visit_num == 0:
                        visit_duration = random.uniform(20, 35) + waiting_time  # Первый дольше
                    else:
                        visit_duration = random.uniform(15, 25) + waiting_time * 0.5  # Последующие быстрее
                    successful = True

                schedule.append({
                    'clinic_id': clinic_id,
                    'district': current_district,
                    'visit_num': len(schedule) + 1,
                    'successful': successful,
                    'duration': visit_duration,
                    'waiting_time': waiting_time,
                    'travel_distance': travel_distance if visit_num == 0 else 0,
                    'time_of_day': time_of_day,
                    'available_doctors': available_doctors_now,
                    'same_clinic_return': same_clinic_return if 'same_clinic_return' in locals() else False
                })

                remaining_visits -= 1
                if remaining_visits <= 0:
                    break

        # ★ РАСЧЁТ ИТОГОВ С УЧЁТОМ ЛОГИКИ ПЛОТНОСТИ ★
        successful_visits = sum(1 for v in schedule if v['successful'])
        total_visit_time = sum(v['duration'] for v in schedule if v['successful'])
        total_waiting_time = sum(v['waiting_time'] for v in schedule)

        # Время на перемещение (меньше в больших городах из-за плотности!)
        if is_big_city:
            travel_efficiency = 0.9  # В Москве/Питере лучше маршруты
        elif density_factors['districts'] >= 5:
            travel_efficiency = 0.8
        else:
            travel_efficiency = 0.7

        total_travel_time = (total_travel_distance / transport_speed * 60 * travel_efficiency) + \
                            (len([d for d in visited_clinics_by_district.values() if d]) * transport_waiting)

        total_time_minutes = total_visit_time + total_waiting_time + total_travel_time
        total_hours = total_time_minutes / 60

        # ★ ЭФФЕКТИВНОСТЬ: в больших городах выше из-за плотности ★
        base_efficiency = (total_visit_time / total_time_minutes * 100) if total_time_minutes > 0 else 0
        if is_big_city:
            efficiency = min(95, base_efficiency * 1.15)  # +15% в Москве/Питере
        elif density_factors['districts'] >= 5:
            efficiency = min(90, base_efficiency * 1.05)  # +5% в крупных
        else:
            efficiency = base_efficiency

        return {
            'total_hours': total_hours,
            'successful_visits': successful_visits,
            'attempted_visits': target_visits,
            'success_rate': successful_visits / target_visits if target_visits > 0 else 0,
            'total_travel_distance_km': total_travel_distance,
            'total_travel_time_min': total_travel_time,
            'total_visit_time_min': total_visit_time,
            'total_waiting_time_min': total_waiting_time,
            'districts_visited': len(available_districts),
            'clinics_visited': sum(len(clinics) for clinics in visited_clinics_by_district.values()),
            'visits_per_clinic': successful_visits / sum(
                len(clinics) for clinics in visited_clinics_by_district.values()) if any(
                visited_clinics_by_district.values()) else 0,
            'efficiency': efficiency,
            'is_big_city': is_big_city,
            'available_districts_today': available_districts,
            'detailed_schedule': schedule
        }

    def calculate_city_load_with_density(self, city, specialization, transport_type,
                                         total_visits_needed, visits_per_doctor,
                                         project_calendar_days,
                                         work_days_per_week=5, max_work_hours_per_day=8):
        """
        Расчёт проекта с учётом плотности врачей
        """
        try:
            # ★ МОДЕЛИРУЕМ 30 РАБОЧИХ ДНЕЙ для статистики ★
            daily_results = []
            for _ in range(30):
                day_result = self.simulate_density_day(
                    city, specialization, visits_per_doctor, transport_type
                )
                daily_results.append(day_result)

            # Средние показатели
            avg_hours_per_day = np.mean([r['total_hours'] for r in daily_results])
            avg_success_rate = np.mean([r['success_rate'] for r in daily_results])
            avg_successful_visits = np.mean([r['successful_visits'] for r in daily_results])

            # ★ РАСЧЁТ ПРОЕКТА ★
            effective_visits_needed = total_visits_needed / avg_success_rate
            unique_doctors_needed = math.ceil(effective_visits_needed / visits_per_doctor)
            total_time_all_doctors_hours = unique_doctors_needed * avg_hours_per_day

            # Доступное время
            project_weeks = project_calendar_days / 7
            total_work_days = project_weeks * work_days_per_week
            total_project_hours = total_work_days * max_work_hours_per_day

            # Учитываем, что в больших городах эффективность выше из-за территориального деления
            density_factors = self.calculate_density_factors(city, specialization)
            efficiency_factor = 0.85
            if density_factors and density_factors['districts'] >= 8:
                efficiency_factor = 0.90  # В Москве/Питере выше эффективность

            available_hours_per_rep = total_project_hours * efficiency_factor

            # Количество медпредов
            min_reps_needed = total_time_all_doctors_hours / available_hours_per_rep
            min_reps_needed_int = math.ceil(min_reps_needed)

            # Оптимальное количество (75% загрузка)
            optimal_reps_needed = total_time_all_doctors_hours / (available_hours_per_rep * 0.75)
            optimal_reps_needed_int = math.ceil(optimal_reps_needed)

            # Сценарии
            scenarios = self._generate_scenarios(
                total_time_all_doctors_hours, available_hours_per_rep,
                work_days_per_week, project_calendar_days,
                min_reps_needed_int, optimal_reps_needed_int
            )

            return {
                'city': city,
                'specialization': specialization,
                'transport_type': transport_type,
                'input_params': {
                    'total_visits_needed': total_visits_needed,
                    'visits_per_doctor': visits_per_doctor,
                    'project_calendar_days': project_calendar_days,
                    'work_days_per_week': work_days_per_week,
                    'max_work_hours_per_day': max_work_hours_per_day,
                    'calculation_method': 'density_based_v2'
                },
                'calculations': {
                    'avg_hours_per_day': round(avg_hours_per_day, 2),
                    'avg_success_rate': round(avg_success_rate * 100, 1),
                    'unique_doctors_needed': unique_doctors_needed,
                    'total_time_all_doctors_hours': round(total_time_all_doctors_hours, 1),
                    'total_project_hours': round(total_project_hours, 1),
                    'min_reps_needed': min_reps_needed_int,
                    'optimal_reps_needed': optimal_reps_needed_int,
                    'efficiency_factor': efficiency_factor
                },
                'daily_statistics': {
                    'avg_successful_visits': round(avg_successful_visits, 1),
                    'avg_travel_distance': round(np.mean([r['total_travel_distance_km'] for r in daily_results]), 1),
                    'districts_per_day_avg': round(np.mean([r['districts_visited'] for r in daily_results]), 1),
                    'clinics_per_day_avg': round(np.mean([r['clinics_visited'] for r in daily_results]), 1)
                },
                'scenarios': scenarios,
                'standard_day_example': {
                    'visits_per_day': visits_per_doctor,
                    'successful_visits': round(avg_successful_visits, 1),
                    'work_hours': round(avg_hours_per_day, 2),
                    'distance_km': round(np.mean([r['total_travel_distance_km'] for r in daily_results]), 1),
                    'success_rate': round(avg_success_rate * 100, 1)
                }
            }

        except Exception as e:
            print(f"Ошибка в density расчете: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Ошибка density расчёта: {str(e)}"}

    def _generate_scenarios(self, total_hours_needed, available_hours_per_rep,
                            work_days_per_week, project_calendar_days,
                            min_reps, optimal_reps):
        """Генерация сценариев"""
        scenarios = []

        min_to_show = max(1, min_reps - 2)
        max_to_show = max(min_reps + 5, optimal_reps + 3)

        for reps in range(min_to_show, max_to_show + 1):
            if reps < 1:
                continue

            # Время выполнения
            weeks_needed = total_hours_needed / (reps * work_days_per_week * 8 * 0.85)
            calendar_days_needed = weeks_needed * 7

            # Процент использования сроков
            time_util = (calendar_days_needed / project_calendar_days) * 100

            # Загрузка персонала
            rep_load = (total_hours_needed / (reps * available_hours_per_rep)) * 100

            # Рекомендация
            if reps == min_reps:
                rec = "Минимальное (напряжённый режим)"
            elif reps == optimal_reps:
                rec = "Оптимальное (рекомендуется)"
            elif rep_load > 90:
                rec = "Перегрузка"
            elif rep_load < 60:
                rec = "Недогрузка"
            else:
                rec = "Хорошая загрузка"

            scenarios.append({
                'reps_count': reps,
                'weeks': round(weeks_needed, 1),
                'work_days': round(weeks_needed * work_days_per_week, 0),
                'calendar_days': round(calendar_days_needed, 0),
                'time_utilization': round(time_util, 1),
                'rep_utilization': round(rep_load, 1),
                'recommendation': rec,
                'is_minimal': reps == min_reps,
                'is_optimal': reps == optimal_reps
            })

        return scenarios

    def _fallback_calculation(self, city, specialization, target_visits, transport_type):
        """Запасной расчет"""
        return {
            'total_hours': target_visits * 0.8,
            'successful_visits': int(target_visits * 0.85),
            'attempted_visits': target_visits,
            'success_rate': 0.85,
            'total_travel_distance_km': target_visits * 3.5,
            'total_travel_time_min': target_visits * 15,
            'total_visit_time_min': target_visits * 25,
            'total_waiting_time_min': target_visits * 10,
            'districts_visited': 1,
            'clinics_visited': target_visits // 3,
            'visits_per_clinic': 3,
            'efficiency': 65,
            'is_big_city': False,
            'detailed_schedule': []
        }

    def calculate_city_density_stats(self, city, specialization):
        """Рассчитывает статистику плотности для города"""
        city_data = self.cities_data.get(city, {})
        if not city_data:
            return None

        # Определяем ключ специализации
        spec_lower = specialization.lower()
        if 'кардиолог' in spec_lower:
            spec_key = 'cardio'
        elif 'терапевт' in spec_lower:
            spec_key = 'therapy'
        elif 'педиатр' in spec_lower:
            spec_key = 'pediatric'
        elif 'аптек' in spec_lower:
            spec_key = 'pharmacy'
        else:
            spec_key = 'therapy'

        # Врачей на поликлинику
        doctors_per_clinic = city_data['doctors_per_polyclinic'].get(spec_key, 2)

        # Площадь на поликлинику (км²)
        area_per_clinic = city_data['city_area_km2'] / city_data['polyclinics']

        # Среднее расстояние между поликлиниками
        avg_distance = math.sqrt(area_per_clinic) * 1.5

        # Классификация города по плотности
        if city in ['Москва', 'Санкт-Петербург']:
            density_class = 'очень высокая'
            max_districts_per_rep = 2
            efficiency_boost = 1.15
        elif doctors_per_clinic >= 4:
            density_class = 'высокая'
            max_districts_per_rep = 3
            efficiency_boost = 1.05
        elif doctors_per_clinic >= 2:
            density_class = 'средняя'
            max_districts_per_rep = 4
            efficiency_boost = 1.0
        else:
            density_class = 'низкая'
            max_districts_per_rep = 5
            efficiency_boost = 0.9

        return {
            'doctors_per_clinic': doctors_per_clinic,
            'area_per_clinic_km2': round(area_per_clinic, 2),
            'avg_distance_between_clinics_km': round(avg_distance, 2),
            'density_class': density_class,
            'max_districts_per_rep': max_districts_per_rep,
            'efficiency_boost': efficiency_boost,
            'districts': city_data['districts'],
            'polyclinics': city_data['polyclinics'],
            'recommendation': self._get_density_recommendation(city, density_class, doctors_per_clinic)
        }

    def calculate_city_density_stats(self, city, specialization):
        """Рассчитывает статистику плотности для города"""
        city_data = self.cities_data.get(city, {})
        if not city_data:
            return None

        # Определяем ключ специализации
        spec_lower = specialization.lower()
        if 'кардиолог' in spec_lower:
            spec_key = 'cardio'
        elif 'терапевт' in spec_lower:
            spec_key = 'therapy'
        elif 'педиатр' in spec_lower:
            spec_key = 'pediatric'
        elif 'аптек' in spec_lower:
            spec_key = 'pharmacy'
        else:
            spec_key = 'therapy'

        # Врачей на поликлинику
        doctors_per_clinic = city_data['doctors_per_polyclinic'].get(spec_key, 2)

        # Площадь на поликлинику (км²)
        area_per_clinic = city_data['city_area_km2'] / city_data['polyclinics']

        # Среднее расстояние между поликлиниками
        avg_distance = math.sqrt(area_per_clinic) * 1.5

        # Классификация города по плотности
        if city in ['Москва', 'Санкт-Петербург']:
            density_class = 'очень высокая'
            max_districts_per_rep = 2
            efficiency_boost = 1.15
        elif doctors_per_clinic >= 4:
            density_class = 'высокая'
            max_districts_per_rep = 3
            efficiency_boost = 1.05
        elif doctors_per_clinic >= 2:
            density_class = 'средняя'
            max_districts_per_rep = 4
            efficiency_boost = 1.0
        else:
            density_class = 'низкая'
            max_districts_per_rep = 5
            efficiency_boost = 0.9

        return {
            'doctors_per_clinic': doctors_per_clinic,
            'area_per_clinic_km2': round(area_per_clinic, 2),
            'avg_distance_between_clinics_km': round(avg_distance, 2),
            'density_class': density_class,
            'max_districts_per_rep': max_districts_per_rep,
            'efficiency_boost': efficiency_boost,
            'districts': city_data['districts'],
            'polyclinics': city_data['polyclinics'],
            'recommendation': self._get_density_recommendation(city, density_class, doctors_per_clinic)
        }

    def _get_density_recommendation(self, city, density_class, doctors_per_clinic):
        """Получить рекомендацию на основе плотности"""
        if city in ['Москва', 'Санкт-Петербург']:
            return "Работать в 1-2 соседних районах. Возвращаться в те же поликлиники в разное время дня."
        elif density_class == 'очень высокая' or density_class == 'высокая':
            return f"В поликлинике в среднем {doctors_per_clinic:.1f} врача. Можно планировать несколько визитов в одну поликлинику."
        else:
            return "Низкая плотность. Планируйте маршрут между несколькими поликлиниками."
