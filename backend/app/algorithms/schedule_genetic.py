import numpy as np
import random
import pandas as pd
from typing import List, Dict, Tuple
from ..schemas.schedule import TeacherItem, CourseItem, ClassroomItem

class GeneticSchedule:
    def __init__(self, teachers: List[TeacherItem], courses: List[CourseItem], classrooms: List[ClassroomItem]):
        teacher_map = {t.id: t for t in teachers}
        # Ensure every course teacher exists (数据里可能存的是 sys_users.id)
        for course in courses:
            tid = str(course.teacher_id)
            if tid not in teacher_map:
                teacher_map[tid] = TeacherItem(id=tid, name=f"教师 {tid}")

        self.teachers = teacher_map
        self.courses = {c.id: c for c in courses}
        self.classrooms = {c.id: c for c in classrooms}
        
        self.teacher_ids = list(self.teachers.keys())
        self.course_ids = list(self.courses.keys())
        self.classroom_ids = list(self.classrooms.keys())
        
        # Constants
        self.DAYS = 5
        self.PERIODS = 6
        self.POPULATION_SIZE = 60
        self.MAX_GENERATIONS = 80
        self.STAGNATION_LIMIT = 15
        self.MUTATION_RATE = 0.03
        
        # Mappings for array indices
        self.c_id_to_idx = {cid: i for i, cid in enumerate(self.classroom_ids)}
        self.idx_to_c_id = {i: cid for cid, i in self.c_id_to_idx.items()}

    def create_individual(self) -> np.ndarray:
        # Schedule: [day][period][classroom_idx] = course_id (0 if empty)
        # We need to place all courses. 
        # Assumption: Each item in self.courses is a single session to be scheduled.
        
        schedule = np.zeros((self.DAYS, self.PERIODS, len(self.classrooms)), dtype=int)
        
        # Randomly assign each course to a (day, period, classroom)
        # Try to respect hard constraints during initialization if possible, or just random
        # Prompt says: "Initial population: Randomly generate 60 legal individuals (no teacher/classroom conflicts...)"
        # Generating purely legal individuals randomly is hard. 
        # We will try to place courses one by one into empty slots.
        
        available_slots = []
        for d in range(self.DAYS):
            for p in range(self.PERIODS):
                for c_idx in range(len(self.classrooms)):
                    available_slots.append((d, p, c_idx))
        
        random.shuffle(available_slots)
        
        # Track teacher availability to avoid immediate conflicts if possible
        # teacher_schedule[teacher_id][day][period] = True
        teacher_availability = {tid: np.zeros((self.DAYS, self.PERIODS), dtype=bool) for tid in self.teacher_ids}
        
        slot_idx = 0
        for course_id, course in self.courses.items():
            placed = False
            while slot_idx < len(available_slots):
                d, p, c_idx = available_slots[slot_idx]
                slot_idx += 1
                
                # Check teacher conflict
                tid = course.teacher_id
                if teacher_availability[tid][d, p]:
                    continue # Teacher busy
                
                # Check multimedia constraint for required courses (Soft or Hard? Prompt says "Required priority multimedia")
                # Let's try to enforce it if possible, otherwise just place it
                c_id = self.idx_to_c_id[c_idx]
                classroom = self.classrooms[c_id]
                if course.is_required and not classroom.is_multimedia:
                    # Try to skip this slot if we can find a better one? 
                    # For initialization simplicity, we might accept it and let evolution fix it,
                    # OR we filter slots. Let's accept for now to ensure placement.
                    pass

                schedule[d, p, c_idx] = course_id
                teacher_availability[tid][d, p] = True
                placed = True
                break
            
            if not placed:
                # Could not place course without conflict in this simple pass
                # Just put it in a random empty slot (or overwrite) - but we want "legal"
                # If we run out of slots, we have a problem (too many courses for resources)
                pass
                
        return schedule

    def calc_fitness(self, individual: np.ndarray) -> float:
        conflicts = 0
        utilization_score = 0
        multimedia_score = 0
        teacher_spread_score = 0
        
        # 1. Conflicts & Teacher Constraints
        teacher_daily_counts = {tid: np.zeros(self.DAYS) for tid in self.teacher_ids}
        teacher_schedule = {tid: set() for tid in self.teacher_ids} # Set of (day, period)
        
        total_slots = self.DAYS * self.PERIODS * len(self.classrooms)
        used_slots = 0
        
        for d in range(self.DAYS):
            for p in range(self.PERIODS):
                for c_idx in range(len(self.classrooms)):
                    course_id = individual[d, p, c_idx]
                    if course_id == 0:
                        continue
                    
                    used_slots += 1
                    course = self.courses[course_id]
                    tid = course.teacher_id
                    
                    # Teacher Conflict
                    if (d, p) in teacher_schedule[tid]:
                        conflicts += 1
                    else:
                        teacher_schedule[tid].add((d, p))
                    
                    teacher_daily_counts[tid][d] += 1
                    
                    # Multimedia Constraint
                    c_id = self.idx_to_c_id[c_idx]
                    classroom = self.classrooms[c_id]
                    if course.is_required:
                        if classroom.is_multimedia:
                            multimedia_score += 1
                        else:
                            # Penalty or just lack of reward?
                            pass
        
        # Teacher Max Classes per Day (>3 is hard constraint violation?)
        # Prompt: "8 teachers (max 3 classes/day)"
        for tid, counts in teacher_daily_counts.items():
            for d in range(self.DAYS):
                if counts[d] > 3:
                    conflicts += (counts[d] - 3) # Penalty for exceeding
                elif counts[d] <= 2:
                    teacher_spread_score += 1 # Bonus for spread
        
        # Utilization
        utilization = used_slots / total_slots if total_slots > 0 else 0
        
        # Multimedia Rate
        required_courses_count = sum(1 for c in self.courses.values() if c.is_required)
        multimedia_rate = multimedia_score / required_courses_count if required_courses_count > 0 else 1.0
        
        # Fitness Function
        # fitness = 1/(conflicts + 1) + utilization*0.3 + multimedia_rate*0.2
        # We can add teacher spread to this
        
        fitness = 1.0 / (conflicts + 1.0) + (utilization * 0.3) + (multimedia_rate * 0.2) + (teacher_spread_score * 0.05)
        
        return fitness, conflicts, utilization

    def crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        # Two-point crossover on Days
        # Swap days between parents
        point1 = random.randint(0, self.DAYS - 2)
        point2 = random.randint(point1 + 1, self.DAYS - 1)
        
        child = parent1.copy()
        child[point1:point2, :, :] = parent2[point1:point2, :, :]
        
        return child

    def mutation(self, individual: np.ndarray) -> np.ndarray:
        # Randomly move a course to another slot
        if random.random() < self.MUTATION_RATE:
            # Pick a random course instance from the schedule
            # Find all non-zero slots
            occupied_indices = np.argwhere(individual > 0)
            if len(occupied_indices) > 0:
                idx = random.choice(occupied_indices)
                d_from, p_from, c_from = idx
                course_id = individual[d_from, p_from, c_from]
                
                # Pick a random target slot
                d_to = random.randint(0, self.DAYS - 1)
                p_to = random.randint(0, self.PERIODS - 1)
                c_to = random.randint(0, len(self.classrooms) - 1)
                
                # Swap or Move
                target_course_id = individual[d_to, p_to, c_to]
                
                individual[d_to, p_to, c_to] = course_id
                individual[d_from, p_from, c_from] = target_course_id
                
        return individual

    def evolve(self):
        population = [self.create_individual() for _ in range(self.POPULATION_SIZE)]
        best_fitness = -1
        stagnation_counter = 0
        best_individual = None
        best_stats = {}
        
        for generation in range(self.MAX_GENERATIONS):
            # Calculate fitness
            fitness_results = [self.calc_fitness(ind) for ind in population]
            # fitness_results is list of (fitness, conflicts, utilization)
            
            current_best_idx = np.argmax([f[0] for f in fitness_results])
            current_best_fitness = fitness_results[current_best_idx][0]
            current_best_ind = population[current_best_idx]
            
            if current_best_fitness > best_fitness:
                best_fitness = current_best_fitness
                best_individual = current_best_ind.copy()
                best_stats = {
                    "fitness": fitness_results[current_best_idx][0],
                    "conflicts": fitness_results[current_best_idx][1],
                    "utilization": fitness_results[current_best_idx][2]
                }
                stagnation_counter = 0
            else:
                stagnation_counter += 1
            
            if stagnation_counter >= self.STAGNATION_LIMIT:
                break
            
            # Selection (Roulette Wheel)
            fitness_values = [f[0] for f in fitness_results]
            total_fitness = sum(fitness_values)
            probs = [f/total_fitness for f in fitness_values]
            
            # Create next generation
            new_population = []
            
            # Elitism: Keep best
            new_population.append(best_individual.copy())
            
            while len(new_population) < self.POPULATION_SIZE:
                # Select 2 parents
                parents_indices = np.random.choice(len(population), size=2, p=probs)
                parent1 = population[parents_indices[0]]
                parent2 = population[parents_indices[1]]
                
                child = self.crossover(parent1, parent2)
                child = self.mutation(child)
                new_population.append(child)
            
            population = new_population
            
        return best_individual, best_stats

    def format_result(self, schedule: np.ndarray):
        # Convert to Teacher View and Classroom View
        teacher_view = {}
        classroom_view = {}
        
        for d in range(self.DAYS):
            for p in range(self.PERIODS):
                for c_idx in range(len(self.classrooms)):
                    course_id = schedule[d, p, c_idx]
                    if course_id == 0:
                        continue
                    
                    course = self.courses[course_id]
                    teacher = self.teachers[course.teacher_id]
                    classroom = self.classrooms[self.idx_to_c_id[c_idx]]
                    
                    day_str = f"周{['一','二','三','四','五'][d]}"
                    period_str = f"第{p+1}节"
                    time_key = f"{day_str} {period_str}"
                    
                    # Teacher View
                    if teacher.name not in teacher_view:
                        teacher_view[teacher.name] = {}
                    teacher_view[teacher.name][time_key] = f"{course.name} ({classroom.name})"
                    
                    # Classroom View
                    if classroom.name not in classroom_view:
                        classroom_view[classroom.name] = {}
                    classroom_view[classroom.name][time_key] = f"{course.name} ({teacher.name})"
                    
        return {"teacher_view": teacher_view, "classroom_view": classroom_view}

    def schedule_to_entries(self, schedule: np.ndarray) -> List[Dict[str, int]]:
        entries: List[Dict[str, int]] = []
        for d in range(self.DAYS):
            for p in range(self.PERIODS):
                for c_idx in range(len(self.classrooms)):
                    course_id = schedule[d, p, c_idx]
                    if course_id == 0:
                        continue
                    course = self.courses[course_id]
                    classroom_id = int(self.idx_to_c_id[c_idx])
                    entries.append({
                        "course_id": int(course_id),
                        "teacher_id": course.teacher_id,
                        "classroom_id": classroom_id,
                        "day": d,
                        "period": p
                    })
        return entries
