# @title Stewart Platform Class
import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt

class StewartPlatform:

    def __init__(self, r_b , phi_b , r_p, phi_p):
        self.r_b = r_b # radius of base
        self.phi_b = phi_b # angle between base joints
        self.r_p = r_p # radius of platform
        self.phi_p = phi_p # angle between platform joints
        # self.options = {
        #     1: self.getSingularValueIndex,
        #     2: self.getManipulabilityIndex,
        #     3: self.getConditionNumber,
        #     4: self.getLocalConditionIndex,
        #     5: self.getLDI,
        #     6: self.getLocalConditionIndexT
        # }
        
    ############################################ IK ##############################################
    def inverse_kinematics(self, pose): ## Inverse Kinematics (Vectorial Closing Loop)
        if len(pose) != 6:
            raise ValueError("Pose must be a 6-element list or array")

        self.p_i = np.zeros([6, 3])
        self.b_i = np.zeros([6, 3])
        self.l_i = np.zeros([6, 3])
        self.l_i_unit = np.zeros([6, 3])

        self.pose_vect = pose
        x_p, y_p, z_p, roll, pitch, yaw = pose

        self.r = R.from_euler("ZYX", (yaw, pitch, roll), degrees=True)  #rotation matrix
        angles = np.array([0, 120, 120, 240, 240, 0])

        for i in range(6):
            j = -1 if (i % 2) == 1 else 1
            self.b_i[i, 0] = self.r_b * np.cos(np.deg2rad(angles[i] + j * self.phi_b / 2)) # base points
            self.b_i[i, 1] = self.r_b * np.sin(np.deg2rad(angles[i] + j * self.phi_b / 2))
            self.p_i[i, 0] = self.r_p * np.cos(np.deg2rad(angles[i] + j * self.phi_p / 2)) # platform points
            self.p_i[i, 1] = self.r_p * np.sin(np.deg2rad(angles[i] + j * self.phi_p / 2))
            self.l_i[i, :] = np.array([x_p, y_p, z_p]) + self.r.as_matrix().dot(self.p_i[i]) - self.b_i[i] # legs vectors
            self.l_i_unit[i, :] = self.l_i[i, :] / np.linalg.norm(self.l_i[i, :]) # unit legs vectors
            self.p_i[i] = self.l_i[i, :] + self.b_i[i] # moving platform points wrt base frame

        return self.l_i
    
    def jacobian(self): # Calculate Jacobian q_dot=Jacobian*x_dot
        if not hasattr(self, 'l_i_unit') or not hasattr(self, 'p_i'):
            raise AttributeError("Run inverse kinematics before calculating the Jacobian")
        self.jacobian = np.zeros([6, 6])
        for i in range(6):
            lastcols = np.cross(self.r.as_matrix().dot(self.p_i[i]), self.l_i_unit[i])
            self.jacobian[i, :3] = self.l_i_unit[i]
            self.jacobian[i, 3:] = lastcols

        return self.jacobian
    
    def forward_kinematics(self, starting_pose, lengths_desired): # Newton Method Optimization.
        if not isinstance(starting_pose, (list, np.ndarray)) or len(starting_pose) != 6:
            raise ValueError("Starting pose must be a list or numpy array with 6 elements")
        if not isinstance(lengths_desired, (list, np.ndarray)) or len(lengths_desired) != 6:
            raise ValueError("Lengths desired must be a list or numpy array with 6 elements")

        self.pose_vect = starting_pose
        x_p, y_p, z_p, roll, pitch, yaw = starting_pose
        self.r = R.from_euler("ZYX", (yaw, pitch, roll), degrees=True)

        # Newton Method Parameters
        max_count = 100
        epsilon = 0.0001
        alpha_pos = 0.2
        alpha_rot = 0.5
        # variables
        est_pose_vect = np.copy(starting_pose)
        est_pose = np.zeros([4, 4])
        est_pose[:3, :3] = self.r.as_matrix()
        est_pose[:3, 3] = [x_p, y_p, z_p]
        est_pose[3, 3] = 1
        delta_lengths = np.zeros(6)
        delta_T = np.identity(4)
        error = epsilon + 1
        count = 0

        while error > epsilon and count < max_count:
            # find new variables
            legs_est = self.inverse_kinematics(est_pose_vect)
            lengths_est = np.linalg.norm(legs_est, axis=1)
            delta_lengths = lengths_desired - lengths_est
            J = self.jacobian()
            J_T = J.transpose()
            # find x_delta with pseudoinverse
            J_star = np.linalg.inv(J_T.dot(J) + 0.0001 * np.identity(6)).dot(J_T)
            x_delta = np.dot(J_star, delta_lengths)
            x_delta_pos = x_delta[:3] * alpha_pos
            x_delta_rot = x_delta[3:] * alpha_rot
            # transform x_delta to delta_T
            r_delta = R.from_euler("ZYX", x_delta_rot)
            delta_T[:3, :3] = r_delta.as_matrix()
            delta_T[:3, 3] = x_delta[:3]
            # move pose
            est_pose = np.dot(delta_T, est_pose)
            # transform est_pose to est_pose_vect
            est_pose_vect[:3] = est_pose[:3, 3]
            self.r_pos = R.from_matrix(est_pose[:3, :3])
            est_pose_vect[3:] = self.r_pos.as_euler("ZYX", degrees=True)
            # find error and update counter
            error = np.linalg.norm(delta_lengths)
            count += 1

        if count < max_count:
            self.pose_vect = est_pose_vect
            print("Forward Kinematics converged!")
            print("Estimated pose:", est_pose_vect)
            print("Desired Lengths:", lengths_desired)
            print("Estimated Lengths:", lengths_est)
            print("Error:", error)
            print("Iterations:", count)
        else:
            print("Forward Kinematics did not converge")
            print("Estimated pose:", est_pose_vect)
            print("Desired Lengths:", lengths_desired)
            print("Estimated Lengths:", lengths_est)
            print("Error:", error)
            print("Iterations:", count)

        return self.pose_vect
    
    
# Define parameters
r_b = 100  # Radius of base
phi_b = 50  # Angle between base joints
r_p = 80  # Radius of platform
phi_p = 80  # Angle between platform joints

# Create Stewart Platform instance
platform = StewartPlatform(r_b, phi_b, r_p, phi_p)

print(np.linalg.norm((StewartPlatform.inverse_kinematics(platform, [0,0,1,5,0,0])),axis=1))

print(StewartPlatform.jacobian(platform))